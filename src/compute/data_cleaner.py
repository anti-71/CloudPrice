"""数据清洗模块

清洗 ODS 层数据，输出 DWD 层

清洗规则：
1. 删除 price <= 0 的记录
2. 删除 sales < 0 的记录
3. 删除商品名称为空的记录
4. 删除价格异常暴涨（10倍以上）的记录
5. 去除重复报价（相同 SKU、平台、店铺、日期）
"""

import statistics
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from src.models import CleanPriceRecord, RawPriceRecord


class DataCleaner:
    """数据清洗器"""

    def clean(self, raw_records: List[RawPriceRecord]) -> List[CleanPriceRecord]:
        """执行数据清洗"""
        if not raw_records:
            return []

        original_count = len(raw_records)

        # 规则1: 删除 price <= 0
        step1 = [r for r in raw_records if r.price > 0]

        # 规则2: 删除 sales < 0
        step2 = [r for r in step1 if r.sales >= 0]

        # 规则3: 删除商品名称为空
        step3 = [r for r in step2 if r.product_name and r.product_name.strip()]

        # 规则4: 删除价格异常暴涨（10倍以上）
        median_prices = self._calculate_median_price(step3)
        step4 = [
            r for r in step3
            if r.sku_id not in median_prices
            or median_prices[r.sku_id] <= 0
            or r.price <= median_prices[r.sku_id] * 10
        ]

        # 规则5: 去除重复报价
        seen: Set[Tuple[str, str, str, str]] = set()
        step5: List[RawPriceRecord] = []
        for r in step4:
            key = (r.date, r.sku_id, r.platform, r.shop_id)
            if key not in seen:
                seen.add(key)
                step5.append(r)

        # 转换为 CleanPriceRecord
        clean_records = [self._to_clean(r) for r in step5]

        logger = get_logger()
        logger.info(
            "Cleaning complete: %d raw -> %d clean (removed %d)",
            original_count, len(clean_records), original_count - len(clean_records)
        )
        return clean_records

    @staticmethod
    def _calculate_median_price(records: List[RawPriceRecord]) -> Dict[str, float]:
        """计算同一 SKU 的价格中位数"""
        price_map: Dict[str, List[float]] = defaultdict(list)
        for r in records:
            price_map[r.sku_id].append(r.price)

        median_map: Dict[str, float] = {}
        for sku_id, prices in price_map.items():
            median_map[sku_id] = statistics.median(prices)
        return median_map

    @staticmethod
    def _to_clean(raw: RawPriceRecord) -> CleanPriceRecord:
        """RawPriceRecord 转为 CleanPriceRecord"""
        return CleanPriceRecord(
            date=raw.date, sku_id=raw.sku_id, product_id=raw.product_id,
            product_name=raw.product_name, category_l1=raw.category_l1,
            category_l2=raw.category_l2, brand=raw.brand, platform=raw.platform,
            shop_id=raw.shop_id, price=raw.price, sales=raw.sales,
            is_promo=raw.is_promo, collect_time=raw.collect_time
        )


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
