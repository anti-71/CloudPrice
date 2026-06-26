"""本地存储模块 — 处理本地 CSV/JSON 文件读写"""

import csv
import json
from pathlib import Path
from typing import List


class LocalStorage:
    """本地文件存储"""

    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)

    def write_csv(self, layer: str, filename: str, rows: List[List[str]]) -> Path:
        """写入 CSV 文件"""
        dir_path = self.base_path / layer
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / filename

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

        logger = get_logger()
        logger.info("Wrote CSV: %s (%d rows)", file_path, len(rows))
        return file_path

    def write_json(self, layer: str, filename: str, content: str) -> Path:
        """写入 JSON 文件"""
        dir_path = self.base_path / layer
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger = get_logger()
        logger.info("Wrote JSON: %s", file_path)
        return file_path

    def read_csv(self, layer: str, filename: str) -> List[List[str]]:
        """读取 CSV 文件"""
        file_path = self.base_path / layer / filename
        with open(file_path, "r", encoding="utf-8") as f:
            return list(csv.reader(f))

    def read_json(self, layer: str, filename: str) -> str:
        """读取 JSON 文件"""
        file_path = self.base_path / layer / filename
        return file_path.read_text(encoding="utf-8")

    def exists(self, layer: str, filename: str) -> bool:
        """判断文件是否存在"""
        return (self.base_path / layer / filename).exists()


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
