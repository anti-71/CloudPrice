"""Cloud Price Index 数据模型模块"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class RawPriceRecord:
    """原始价格记录 — ODS 层"""
    date: str = ""
    sku_id: str = ""
    product_id: str = ""
    product_name: str = ""
    category_l1: str = ""
    category_l2: str = ""
    brand: str = ""
    platform: str = ""
    shop_id: str = ""
    price: float = 0.0
    sales: int = 0
    is_promo: bool = False
    collect_time: str = ""


@dataclass
class CleanPriceRecord:
    """清洗后价格记录 — DWD 层"""
    date: str = ""
    sku_id: str = ""
    product_id: str = ""
    product_name: str = ""
    category_l1: str = ""
    category_l2: str = ""
    brand: str = ""
    platform: str = ""
    shop_id: str = ""
    price: float = 0.0
    sales: int = 0
    is_promo: bool = False
    collect_time: str = ""


@dataclass
class SkuDailySummary:
    """SKU 日汇总 — DWS 层"""
    date: str = ""
    sku_id: str = ""
    product_id: str = ""
    product_name: str = ""
    category_l1: str = ""
    category_l2: str = ""
    brand: str = ""
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    total_sales: int = 0
    shop_count: int = 0
    record_count: int = 0


@dataclass
class CategoryDailySummary:
    """类目日汇总 — DWS 层"""
    date: str = ""
    category_l1: str = ""
    category_l2: str = ""
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    total_sales: int = 0
    sku_count: int = 0
    record_count: int = 0


@dataclass
class OverallDailySummary:
    """全网日汇总 — DWS 层"""
    date: str = ""
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    total_sales: int = 0
    total_skus: int = 0
    total_records: int = 0


@dataclass
class PriceIndex:
    """价格指数 — ADS 层"""
    date: str = ""
    category: Optional[str] = None
    sku_id: Optional[str] = None
    product_name: Optional[str] = None
    index_val: float = 0.0
    change_pct: float = 0.0

    def to_dict(self) -> dict:
        """转为字典（驼峰命名，供 DataV 使用），过滤 None 字段"""
        d = {
            "date": self.date,
            "index": self.index_val,
            "changePct": self.change_pct,
        }
        if self.category is not None:
            d["category"] = self.category
        if self.sku_id is not None:
            d["skuId"] = self.sku_id
        if self.product_name is not None:
            d["productName"] = self.product_name
        # 只保留有 index 或 changePct 非零的场景
        return d
