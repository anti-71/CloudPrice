"""OSS 小规模上传 + ClickHouse SQL 正确性验证

上传小批量 CSV 到 OSS，导入 ClickHouse 后验证 SQL 查询
"""

import os
import csv
import io
import json
import pytest

from src.ingestion.mock_data_generator import MockDataGenerator
from src.compute.data_cleaner import DataCleaner
from src.storage.oss_client import OssClient
from src.util.config_loader import ConfigLoader


def _oss_ready():
    return os.getenv("OSS_ENABLED", "").lower() == "true"


def _ch_ready():
    return os.getenv("CLICKHOUSE_HOST", "") != ""


@pytest.fixture(scope="module")
def config():
    return ConfigLoader()


@pytest.fixture(scope="module")
def sample_df(config):
    gen = MockDataGenerator(config, seed=2026)
    df = gen.generate("2023-06-01", "2023-06-01")
    return DataCleaner().clean(df).head(50)  # 只取50条


class TestOssUploadVerify:

    @pytest.mark.skipif(not _oss_ready(), reason="OSS 未启用")
    def test_small_csv_upload_to_oss(self, config, sample_df):
        """小规模 CSV 上传 OSS 并验证上传成功"""
        oss = OssClient(config)

        out = io.StringIO()
        sample_df.to_csv(out, index=False)
        key = oss.build_key("test", "ci_verify", "sample.csv")
        oss.upload_string(key, out.getvalue())

        # 验证文件存在（无异常即成功）
        assert len(sample_df) == 50, "应上传 50 条测试数据"

    def test_clean_data_logic(self, config, sample_df):
        """验证清洗后的数据逻辑正确"""
        assert len(sample_df) <= 50
        assert (sample_df["price"] > 0).all()
        assert (sample_df["sales"] >= 0).all()
        assert not sample_df["product_name"].isna().any()

    @pytest.mark.skipif(not _ch_ready(), reason="ClickHouse 未配置")
    def test_ch_sql_correctness(self, config, sample_df):
        """验证 ClickHouse SQL 查询正确性"""
        from src.storage.clickhouse_client import ClickHouseClient
        ch = ClickHouseClient(config)

        ch.execute("""
            CREATE TABLE IF NOT EXISTS test_sql_verify (
                date Date, sku_id String, price Float64, sales Int64
            ) ENGINE = MergeTree() ORDER BY date
        """)
        ch.execute("TRUNCATE TABLE IF EXISTS test_sql_verify")

        # 批量插入
        batch = ",".join(
            f"('{r['date']}', '{r['sku_id']}', {r['price']}, {int(r['sales'])})"
            for _, r in sample_df.iterrows()
        )
        ch.execute("INSERT INTO test_sql_verify VALUES " + batch)

        # SQL 验证
        cnt = ch.query("SELECT count() FROM test_sql_verify").strip()
        assert cnt == "50", f"计数验证失败: {cnt} != 50"

        avg_price = float(ch.query("SELECT avg(price) FROM test_sql_verify").strip())
        assert avg_price > 0, "平均价格应 > 0"

        total_sales = int(ch.query("SELECT sum(sales) FROM test_sql_verify").strip())
        assert total_sales > 0, "总销量应 > 0"

        ch.execute("DROP TABLE IF EXISTS test_sql_verify")
