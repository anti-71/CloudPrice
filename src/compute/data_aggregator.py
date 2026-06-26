"""数据汇总模块

汇总 DWD 层明细，输出 DWS 层日汇总
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from src.models import CategoryDailySummary, CleanPriceRecord, OverallDailySummary, SkuDailySummary


@dataclass
class AggregationResult:
    """汇总结果容器"""
    sku_summaries: List[SkuDailySummary]
    category_summaries: List[CategoryDailySummary]
    overall_summaries: List[OverallDailySummary]


class DataAggregator:
    """数据汇总器"""

    def aggregate(self, clean_records: List[CleanPriceRecord]) -> AggregationResult:
        """执行数据汇总"""
        if not clean_records:
            return AggregationResult([], [], [])

        # 按日期分组
        by_date: Dict[str, List[CleanPriceRecord]] = defaultdict(list)
        for r in clean_records:
            by_date[r.date].append(r)

        sku_summaries: List[SkuDailySummary] = []
        category_summaries: List[CategoryDailySummary] = []
        overall_summaries: List[OverallDailySummary] = []

        for date_str, day_records in sorted(by_date.items()):
            # SKU 日汇总
            sku_day = self._aggregate_sku(date_str, day_records)
            sku_summaries.extend(sku_day)

            # 类目日汇总
            cat_day = self._aggregate_category(date_str, day_records, sku_day)
            category_summaries.extend(cat_day)

            # 全网日汇总
            overall = self._aggregate_overall(date_str, day_records)
            overall_summaries.append(overall)

        logger = get_logger()
        logger.info(
            "Aggregation complete: %d sku, %d category, %d overall summaries",
            len(sku_summaries), len(category_summaries), len(overall_summaries)
        )
        return AggregationResult(sku_summaries, category_summaries, overall_summaries)

    @staticmethod
    def _aggregate_sku(date_str: str, day_records: List[CleanPriceRecord]) -> List[SkuDailySummary]:
        """SKU 日汇总"""
        by_sku: Dict[str, List[CleanPriceRecord]] = defaultdict(list)
        for r in day_records:
            by_sku[r.sku_id].append(r)

        summaries: List[SkuDailySummary] = []
        for sku_id, sku_records in sorted(by_sku.items()):
            first = sku_records[0]
            prices = [r.price for r in sku_records]
            total_sales = sum(r.sales for r in sku_records)

            summary = SkuDailySummary(
                date=date_str, sku_id=sku_id, product_id=first.product_id,
                product_name=first.product_name, category_l1=first.category_l1,
                category_l2=first.category_l2, brand=first.brand,
                avg_price=round(sum(prices) / len(prices), 2),
                min_price=round(min(prices), 2),
                max_price=round(max(prices), 2),
                total_sales=total_sales, shop_count=len(sku_records),
                record_count=len(sku_records)
            )
            summaries.append(summary)
        return summaries

    @staticmethod
    def _aggregate_category(date_str: str, day_records: List[CleanPriceRecord],
                            sku_summaries: List[SkuDailySummary]) -> List[CategoryDailySummary]:
        """类目日汇总"""
        by_category: Dict[str, List[SkuDailySummary]] = defaultdict(list)
        for s in sku_summaries:
            by_category[s.category_l1].append(s)

        summaries: List[CategoryDailySummary] = []
        for category, cat_skus in sorted(by_category.items()):
            avg_prices = [s.avg_price for s in cat_skus]
            total_sales = sum(s.total_sales for s in cat_skus)

            summary = CategoryDailySummary(
                date=date_str, category_l1=category, category_l2=category,
                avg_price=round(sum(avg_prices) / len(avg_prices), 2),
                min_price=round(min(avg_prices), 2),
                max_price=round(max(avg_prices), 2),
                total_sales=total_sales, sku_count=len(cat_skus),
                record_count=len(cat_skus)
            )
            summaries.append(summary)
        return summaries

    @staticmethod
    def _aggregate_overall(date_str: str, day_records: List[CleanPriceRecord]) -> OverallDailySummary:
        """全网日汇总"""
        prices = [r.price for r in day_records]
        total_sales = sum(r.sales for r in day_records)
        unique_skus = len({r.sku_id for r in day_records})

        return OverallDailySummary(
            date=date_str,
            avg_price=round(sum(prices) / len(prices), 2),
            min_price=round(min(prices), 2),
            max_price=round(max(prices), 2),
            total_sales=total_sales,
            total_skus=unique_skus,
            total_records=len(day_records)
        )


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
