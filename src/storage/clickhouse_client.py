"""ClickHouse 客户端封装 — HTTP 接口"""

import requests

from src.util.config_loader import ConfigLoader


class ClickHouseClient:

    def __init__(self, config: ConfigLoader):
        self.host = config.clickhouse_host
        self.port = config.clickhouse_port
        self.user = config.clickhouse_user
        self.password = config.clickhouse_password
        self.database = config.clickhouse_database
        self.base_url = f"http://{self.host}:{self.port}"
        self._auth = (self.user, self.password)
        # 切换到目标数据库
        self.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        self.execute(f"USE {self.database}")
        get_logger().info(
            "ClickHouse client ready (host: %s, db: %s)", self.host, self.database
        )

    def query(self, sql: str) -> str:
        """执行 SQL 并返回纯文本结果"""
        resp = requests.get(
            self.base_url,
            params={"query": sql},
            auth=self._auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.text

    def query_json(self, sql: str) -> list[dict]:
        """执行 SQL 并返回 JSON 结果"""
        resp = requests.get(
            self.base_url,
            params={"query": sql, "default_format": "JSONEachRow"},
            auth=self._auth,
            timeout=60,
        )
        resp.raise_for_status()
        rows = []
        for line in resp.text.strip().split("\n"):
            if line.strip():
                rows.append(__import__("json").loads(line))
        return rows

    def execute(self, sql: str):
        """执行 DDL/DML 语句（建表、插入等）"""
        resp = requests.post(
            self.base_url,
            params={"query": sql},
            auth=self._auth,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    def ping(self) -> bool:
        """测试连接"""
        try:
            result = self.query("SELECT 1")
            return "1" in result
        except Exception:
            return False


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
