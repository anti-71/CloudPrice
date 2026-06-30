"""模拟数据生成器 — pandas DataFrame 版本"""

import random as _random
import pandas as pd

from src.util.config_loader import ConfigLoader
from src.util.date_utils import format_date, is_weekend

BRANDS = ["华为", "小米", "苹果", "OPPO", "vivo", "联想", "戴尔", "惠普", "海尔", "美的",
          "三只松鼠", "百草味", "优衣库", "耐克", "阿迪达斯", "欧莱雅", "兰蔻", "雅诗兰黛"]

PRICE_RANGES = {
    "手机数码": (500, 8500), "电脑办公": (300, 15000),
    "家用电器": (200, 5200), "食品饮料": (5, 200),
    "服饰鞋包": (50, 1500), "美妆个护": (30, 800),
    "运动户外": (80, 3000), "日用百货": (10, 500),
}


class MockDataGenerator:
    """模拟数据生成器（pandas）"""

    def __init__(self, config: ConfigLoader, seed: int = None):
        self.config = config
        self.rng = _random.Random(seed)
        self._skus = self._build_skus()

    def _build_skus(self) -> list:
        skus = []
        for i in range(1, self.config.sku_count + 1):
            cat = self.rng.choice(self.config.categories)
            lo, hi = PRICE_RANGES.get(cat, (100, 1100))
            skus.append({
                "sku_id": f"SKU{i:04d}",
                "product_id": f"PROD{i:04d}",
                "category_l1": cat,
                "category_l2": f"{cat}子类{self.rng.randint(1,3)}",
                "brand": self.rng.choice(BRANDS),
                "base_price": round(self.rng.uniform(lo, hi), 2),
            })
        return skus

    def generate(self, start_date: str, end_date: str) -> pd.DataFrame:
        """生成指定日期范围的模拟数据，返回 DataFrame"""
        from datetime import date, timedelta
        d = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        dfs = []
        while d <= end:
            dfs.append(self._day_df(d))
            d += timedelta(days=1)
        df = pd.concat(dfs, ignore_index=True)
        get_logger().info("Generated %d raw records (%s → %s)", len(df), start_date, end_date)
        return df

    def _day_df(self, dt) -> pd.DataFrame:
        ds = format_date(dt)
        promo = dt.weekday() in (2, 4)  # 周三/周五促销
        wkend = is_weekend(dt)
        rows = []
        for sku in self._skus:
            for _ in range(self.rng.randint(2, 5)):
                plat = self.rng.choice(self.config.platforms)
                price = sku["base_price"] * (1 + self.rng.uniform(-0.05, 0.05))
                if promo:
                    price *= self.rng.uniform(0.7, 0.9)
                sales = self.rng.randint(50, 250)
                if promo:
                    sales *= self.rng.randint(2, 5)
                if wkend:
                    sales = int(sales * 1.2)
                rows.append({
                    "date": ds, "sku_id": sku["sku_id"], "product_id": sku["product_id"],
                    "product_name": f"{sku['brand']}{sku['category_l1']}{sku['sku_id']}",
                    "category_l1": sku["category_l1"], "category_l2": sku["category_l2"],
                    "brand": sku["brand"], "platform": plat,
                    "shop_id": f"SHOP_{plat}_{self.rng.randint(1,500):04d}",
                    "price": round(price, 2), "sales": sales, "is_promo": 1 if promo else 0,
                    "collect_time": f"{ds} {self.rng.randint(0,23):02d}:{self.rng.randint(0,59):02d}:{self.rng.randint(0,59):02d}",
                })
        df = pd.DataFrame(rows)
        df = _inject_dirty(df, self.config.dirty_data_rate, self.rng)
        return df


def _inject_dirty(df: pd.DataFrame, rate: float, rng) -> pd.DataFrame:
    n = max(1, int(len(df) * rate))
    idxs = rng.sample(range(len(df)), min(n, len(df)))
    for i in idxs:
        t = rng.randint(0, 3)
        if t == 0:  df.at[i, "price"] = -abs(df.at[i, "price"])
        elif t == 1: df.at[i, "sales"] = -abs(df.at[i, "sales"])
        elif t == 2: df.at[i, "product_name"] = ""
        else:         df.at[i, "price"] *= rng.uniform(10, 20)
    get_logger().info("Injected %d dirty records (rate=%.2f)", n, rate)
    return df


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
