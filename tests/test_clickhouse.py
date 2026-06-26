"""ClickHouse 连通性测试"""

import os

import pytest

from src.storage.clickhouse_client import ClickHouseClient
from src.util.config_loader import ConfigLoader


def _clickhouse_available():
    """检查 ClickHouse 是否可达（有凭证且白名单放行）"""
    return os.getenv("CLICKHOUSE_HOST", "") != ""


@pytest.mark.skipif(
    not _clickhouse_available(),
    reason="未配置 ClickHouse 凭证（CI 中请使用 GitHub Secrets）"
)
class TestClickHouseConnection:

    def test_ping(self):
        """测试 ClickHouse 连通性"""
        config = ConfigLoader()
        ch = ClickHouseClient(config)
        assert ch.ping(), "ClickHouse ping 失败"

    def test_version_query(self):
        """测试查询版本号"""
        config = ConfigLoader()
        ch = ClickHouseClient(config)
        result = ch.query("SELECT version() AS v")
        assert "23." in result or "24." in result, f"非预期版本: {result}"

    def test_create_table_and_insert(self):
        """测试建表与插入"""
        config = ConfigLoader()
        ch = ClickHouseClient(config)
        ch.execute("""
            CREATE TABLE IF NOT EXISTS test_connection (
                id UInt32,
                name String
            ) ENGINE = MergeTree()
            ORDER BY id
        """)
        ch.execute("INSERT INTO test_connection VALUES (1, 'hello')")
        result = ch.query("SELECT * FROM test_connection")
        assert "hello" in result
        ch.execute("DROP TABLE IF EXISTS test_connection")
