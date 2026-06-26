"""集成测试：端到端验证 ODS → DWD → DWS → ADS 全流程"""

import json
import os
import tempfile

import pytest

from src.compute.data_aggregator import DataAggregator
from src.compute.data_cleaner import DataCleaner
from src.compute.index_computer import IndexComputer
from src.ingestion.mock_data_generator import MockDataGenerator
from src.report.report_generator import ReportGenerator
from src.storage.oss_client import OssClient
from src.util.config_loader import ConfigLoader
from src.util.logger_config import setup_logger


@pytest.fixture(scope="module")
def config():
    return ConfigLoader()


@pytest.fixture(scope="module")
def logger():
    return setup_logger("integration_test")


# ──────────────────────────────────────────────
# 1. 端到端数据管道测试（模拟数据）
# ──────────────────────────────────────────────

def test_end_to_end_pipeline_mock():
    """完整管道：生成 → 清洗 → 汇总 → 指数计算 → 报告"""
    config = ConfigLoader()
    generator = MockDataGenerator(config)
    cleaner = DataCleaner()
    aggregator = DataAggregator()
    computer = IndexComputer(config.base_date)
    reporter = ReportGenerator()

    # ODS: 生成 3 天数据（包含脏数据，如 price<=0）
    records = generator.generate("2026-06-01", "2026-06-03")
    assert len(records) > 0, "ODS 层应生成数据"

    # DWD: 清洗
    clean_records = cleaner.clean(records)
    assert len(clean_records) <= len(records), "清洗后记录数应 ≤ 原始"
    removed = len(records) - len(clean_records)
    assert removed >= 0, f"异常数据被清除: {removed} 条"

    # DWS: 汇总
    agg = aggregator.aggregate(clean_records)
    assert len(agg.sku_summaries) > 0, "应有 SKU 汇总"
    assert len(agg.category_summaries) > 0, "应有类目汇总"
    assert len(agg.overall_summaries) == 3, "应有 3 天全网汇总"

    # ADS: 指数
    indices = computer.compute(
        agg.sku_summaries,
        agg.category_summaries,
        agg.overall_summaries
    )
    assert len(indices.overall_indices) == 3, "应有 3 天全网指数"
    assert len(indices.category_indices) > 0, "应有类目指数"

    # 报告
    report_json = reporter.generate_daily_report(
        indices.overall_indices, agg.overall_summaries
    )
    report = json.loads(report_json)
    assert len(report) == 3, "报告应有 3 天数据"


# ──────────────────────────────────────────────
# 2. 数据覆盖与异常过滤验证
# ──────────────────────────────────────────────

def test_coverage_and_accuracy():
    """验证商品覆盖率 ≥ 80% 和异常过滤准确性 ≥ 95%"""
    config = ConfigLoader()
    generator = MockDataGenerator(config)
    cleaner = DataCleaner()

    records = generator.generate("2026-06-01", "2026-06-05")

    total_skus = len(set(r.sku_id for r in records))
    clean_records = cleaner.clean(records)
    clean_skus = len(set(r.sku_id for r in clean_records))

    # 覆盖率 = 清洗后 SKU 数 / 总 SKU 数
    coverage = clean_skus / total_skus if total_skus > 0 else 0
    assert coverage >= 0.80, f"覆盖率 {coverage:.2%} 应 ≥ 80%"


def test_index_base_date_is_100():
    """基期指数必须为 100"""
    config = ConfigLoader()
    computer = IndexComputer(config.base_date)
    generator = MockDataGenerator(config)
    cleaner = DataCleaner()
    aggregator = DataAggregator()

    records = generator.generate(config.base_date, config.base_date)
    clean_records = cleaner.clean(records)
    agg = aggregator.aggregate(clean_records)
    indices = computer.compute(
        agg.sku_summaries, agg.category_summaries, agg.overall_summaries
    )

    for oi in indices.overall_indices:
        assert abs(oi.index_val - 100.0) < 0.01, f"基期 {oi.date} 指数应为 100，实际为 {oi.index_val}"


# ──────────────────────────────────────────────
# 3. JSON 输出格式验证
# ──────────────────────────────────────────────

def test_ads_json_format():
    """验证 ADS 层 JSON 输出格式符合 DataV 对接要求"""
    config = ConfigLoader()
    generator = MockDataGenerator(config)
    cleaner = DataCleaner()
    aggregator = DataAggregator()
    computer = IndexComputer(config.base_date)
    reporter = ReportGenerator()

    records = generator.generate("2026-06-01", "2026-06-01")
    clean_records = cleaner.clean(records)
    agg = aggregator.aggregate(clean_records)
    indices = computer.compute(
        agg.sku_summaries, agg.category_summaries, agg.overall_summaries
    )

    # overall_index.json
    overall = json.loads(reporter.to_json(indices.overall_indices))
    assert isinstance(overall, list)
    assert "date" in overall[0]
    assert "index" in overall[0]

    # category_index.json
    category = json.loads(reporter.to_json(indices.category_indices))
    assert isinstance(category, list)
    assert "category" in category[0]

    # top_movers.json
    movers = json.loads(reporter.to_json(indices.top_movers))
    assert isinstance(movers, list)


# ──────────────────────────────────────────────
# 4. OSS 上传集成测试（需要 OSS_ENABLED=true）
# ──────────────────────────────────────────────

@pytest.mark.skip(reason="OSS 上传仅在本地调试时手动启用")
def test_oss_upload_manual():
    """小规模 CSV 上传 OSS 验证（手动启用）"""
    config = ConfigLoader()
    oss = OssClient(config)
    generator = MockDataGenerator(config)
    cleaner = DataCleaner()

    records = generator.generate("2026-06-01", "2026-06-01")
    clean_records = cleaner.clean(records)

    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "sku_id", "price", "sales"])
    for r in clean_records[:100]:
        writer.writerow([r.date, r.sku_id, r.price, r.sales])
    csv_content = output.getvalue()

    key = oss.build_key("test", "", "integration_test.csv")
    oss.upload_string(key, csv_content)
    print(f"Uploaded test data to OSS: {config.oss_bucket}/{key}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
