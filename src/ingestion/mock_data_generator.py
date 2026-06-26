"""模拟数据生成器

生成模拟电商价格数据，按 dirty-data-rate 注入脏数据
"""

import random
from datetime import date, timedelta
from typing import List

from src.models import RawPriceRecord
from src.util.config_loader import ConfigLoader
from src.util.date_utils import format_date, is_weekend

# 品牌池
BRANDS = ["Apple", "华为", "小米", "三星", "索尼", "联想", "海尔", "格力",
          "美的", "NIKE", "Adidas", "欧莱雅", "玉兰油", "良品铺子", "三只松鼠"]


class MockDataGenerator:
    """模拟数据生成器"""

    def __init__(self, config: ConfigLoader, seed: int | None = None):
        self.config = config
        self.random = random.Random(seed)

    def generate(self, start_date: str, end_date: str) -> List[RawPriceRecord]:
        """生成指定日期范围的模拟数据"""
        start = parse_date(start_date)
        end = parse_date(end_date)

        records: List[RawPriceRecord] = []
        platforms = self.config.platforms
        categories = self.config.categories
        sku_count = self.config.sku_count
        dirty_rate = self.config.dirty_data_rate

        current = start
        while current <= end:
            records.extend(self._generate_for_date(current, platforms, categories, sku_count, dirty_rate))
            current += timedelta(days=1)

        logger = get_logger()
        logger.info("Generated %d raw records from %s to %s", len(records), start_date, end_date)
        return records

    def _generate_for_date(self, dt: date, platforms: List[str],
                           categories: List[str], sku_count: int,
                           dirty_rate: float) -> List[RawPriceRecord]:
        """生成单日模拟数据"""
        records: List[RawPriceRecord] = []
        date_str = format_date(dt)
        weekend = is_weekend(dt)

        for i in range(1, sku_count + 1):
            sku_id = f"SKU{i:04d}"
            product_id = f"PROD{i:04d}"
            category = categories[self.random.randint(0, len(categories) - 1)]
            brand = BRANDS[abs(hash(sku_id)) % len(BRANDS)]

            shop_count = self.random.randint(2, 5)
            for _ in range(shop_count):
                platform = platforms[self.random.randint(0, len(platforms) - 1)]
                shop_id = f"SHOP_{platform}_{self.random.randint(1, 500):04d}"
                collect_time = f"{date_str} {self.random.randint(0, 23):02d}:{self.random.randint(0, 59):02d}:{self.random.randint(0, 59):02d}"

                base_price = self._generate_base_price(category)
                price = self._calculate_price(base_price, dt, weekend)
                sales = self._calculate_sales(price, dt, weekend)
                is_promo = self._is_promo_day(dt)
                product_name = self._generate_product_name(category, brand, sku_id)

                record = RawPriceRecord(
                    date=date_str, sku_id=sku_id, product_id=product_id,
                    product_name=product_name, category_l1=category, category_l2=category,
                    brand=brand, platform=platform, shop_id=shop_id,
                    price=price, sales=sales, is_promo=is_promo, collect_time=collect_time
                )
                records.append(record)

        # 注入脏数据
        if dirty_rate > 0:
            self._inject_dirty_data(records, dirty_rate)

        return records

    @staticmethod
    def _generate_base_price(category: str) -> float:
        """不同类目有不同的基准价格区间"""
        ranges = {
            "手机数码": (500, 8500),
            "电脑办公": (300, 10300),
            "家用电器": (200, 5200),
            "食品饮料": (5, 205),
            "服饰鞋包": (50, 1550),
            "美妆个护": (30, 830),
            "运动户外": (80, 3080),
            "日用百货": (10, 510),
        }
        low, high = ranges.get(category, (100, 1100))
        return low + random.random() * (high - low)

    def _calculate_price(self, base_price: float, dt: date, weekend: bool) -> float:
        """日常价格 = 基准价格 ± 5%，促销日打 7-9 折"""
        fluctuation = 1.0 + (self.random.random() - 0.5) * 0.1
        if self._is_promo_day(dt):
            discount = 0.7 + self.random.random() * 0.2
            return round(base_price * fluctuation * discount, 2)
        return round(base_price * fluctuation, 2)

    def _calculate_sales(self, price: float, dt: date, weekend: bool) -> int:
        """计算销量，促销日 2-5 倍，周末 x1.2"""
        base = 50 + self.random.randint(0, 199)
        if self._is_promo_day(dt):
            base *= self.random.randint(2, 5)
        if weekend:
            base = int(base * 1.2)
        return base

    @staticmethod
    def _is_promo_day(dt: date) -> bool:
        """促销日：周三(2)、周五(4)"""
        return dt.weekday() in (2, 4)

    @staticmethod
    def _generate_product_name(category: str, brand: str, sku_id: str) -> str:
        """生成商品名称"""
        names = {
            "手机数码": f"{brand}智能手机 {sku_id}",
            "电脑办公": f"{brand}笔记本电脑 {sku_id}",
            "家用电器": f"{brand}智能家电 {sku_id}",
            "食品饮料": f"{brand}精选零食礼包 {sku_id}",
            "服饰鞋包": f"{brand}时尚运动鞋 {sku_id}",
            "美妆个护": f"{brand}护肤精华 {sku_id}",
            "运动户外": f"{brand}运动装备 {sku_id}",
        }
        return names.get(category, f"{brand}日用商品 {sku_id}")

    def _inject_dirty_data(self, records: List[RawPriceRecord], dirty_rate: float):
        """注入脏数据"""
        dirty_count = max(1, int(len(records) * dirty_rate))
        injected = 0

        while injected < dirty_count:
            idx = self.random.randint(0, len(records) - 1)
            record = records[idx]
            dtype = self.random.randint(0, 4)

            if dtype == 0:
                # price <= 0
                record.price = -abs(record.price) - self.random.random() * 10
            elif dtype == 1:
                # sales < 0
                record.sales = -abs(record.sales) - self.random.randint(1, 10)
            elif dtype == 2:
                # 空名称
                record.product_name = ""
            elif dtype == 3:
                # 价格暴涨 10 倍以上
                record.price = record.price * (10 + self.random.random() * 20)
            elif dtype == 4:
                # 重复报价
                dup = RawPriceRecord(**{k: getattr(record, k) for k in record.__dataclass_fields__})
                records.append(dup)
            injected += 1

        logger = get_logger()
        logger.info("Injected %d dirty records (rate=%.2f)", dirty_count, dirty_rate)


def parse_date(date_str: str) -> date:
    """解析日期字符串"""
    from src.util.date_utils import parse_date as _parse
    return _parse(date_str)


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
