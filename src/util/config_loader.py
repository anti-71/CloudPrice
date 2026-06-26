"""配置加载模块"""

import os
from pathlib import Path
from typing import Any, List

import yaml
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件
load_dotenv()


class ConfigLoader:
    """从 config.yaml 加载配置，支持环境变量覆盖"""

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = str(Path("config") / "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            self._config: dict = yaml.safe_load(f) or {}

    # ---- YAML 配置项 ----

    @property
    def project_name(self) -> str:
        return self._config.get("project-name", "cloud-price-index")

    @property
    def base_date(self) -> str:
        return str(self._config.get("base-date", "2026-06-01"))

    @property
    def start_date(self) -> str:
        return str(self._config.get("start-date", "2026-06-01"))

    @property
    def end_date(self) -> str:
        return str(self._config.get("end-date", "2026-06-30"))

    @property
    def sku_count(self) -> int:
        return int(self._config.get("sku-count", 2000))

    @property
    def platforms(self) -> List[str]:
        return list(self._config.get("platforms", ["淘宝", "京东", "拼多多"]))

    @property
    def categories(self) -> List[str]:
        return list(self._config.get(
            "categories",
            ["手机数码", "电脑办公", "家用电器", "食品饮料",
             "服饰鞋包", "美妆个护", "运动户外", "日用百货"]
        ))

    @property
    def dirty_data_rate(self) -> float:
        return float(self._config.get("dirty-data-rate", 0.02))

    # ---- 环境变量配置项（OSS） ----

    @property
    def oss_enabled(self) -> bool:
        return os.getenv("OSS_ENABLED", "false").lower() == "true"

    @property
    def oss_endpoint(self) -> str:
        return os.getenv("ALIYUN_OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")

    @property
    def oss_bucket(self) -> str:
        return os.getenv("ALIYUN_OSS_BUCKET", "")

    @property
    def oss_access_key_id(self) -> str:
        return os.getenv("ALIYUN_ACCESS_KEY_ID", "")

    @property
    def oss_access_key_secret(self) -> str:
        return os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")

    @property
    def oss_prefix(self) -> str:
        return os.getenv("OSS_PREFIX", "price-index-platform")
