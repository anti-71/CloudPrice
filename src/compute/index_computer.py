"""指数计算模块

基于 DWS 层数据计算各类指数，输出 ADS 层 JSON

计算公式：
- SKU 指数 = (当日均价 / 基期均价) × 100
- 类目指数 = Σ(SKU指数 × SKU销量权重)
- 全网指数 = Σ(类目指数 × 类目销量权重)
- 环比涨跌幅 = (当日指数 / 前一日指数) - 1
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from src.models import CategoryDailySummary, OverallDailySummary, PriceIndex, SkuDailySummary


@dataclass
class IndexResult:
    """指数计算结果容器"""
    overall_indices: List[PriceIndex] = field(default_factory=list)
    category_indices: List[PriceIndex] = field(default_factory=list)
    sku_indices: List[PriceIndex] = field(default_factory=list)
    top_movers: List[PriceIndex] = field(default_factory=list)


class IndexComputer:
    """价格指数计算器"""

    def __init__(self, base_date: str):
        self.base_date = base_date

    def compute(self, sku_summaries: List[SkuDailySummary],
                category_summaries: List[CategoryDailySummary],
                overall_summaries: List[OverallDailySummary]) -> IndexResult:
        """计算所有指数"""
        if not sku_summaries:
            return IndexResult()

        # 1. 计算基期均价
        base_prices = self._compute_base_prices(sku_summaries)

        # 2. 按日期分组
        sku_by_date: Dict[str, List[SkuDailySummary]] = defaultdict(list)
        for s in sku_summaries:
            sku_by_date[s.date].append(s)

        cat_by_date: Dict[str, List[CategoryDailySummary]] = defaultdict(list)
        for c in category_summaries:
            cat_by_date[c.date].append(c)

        sorted_dates = sorted(sku_by_date.keys())

        overall_indices: List[PriceIndex] = []
        category_indices: List[PriceIndex] = []
        sku_indices_list: List[PriceIndex] = []
        top_movers: List[PriceIndex] = []
        prev_overall: Dict[str, float] = {}

        for date_str in sorted_dates:
            day_skus = sku_by_date[date_str]
            day_categories = cat_by_date.get(date_str, [])

            # 计算 SKU 指数
            day_sku_indices = self._compute_sku_indices(date_str, day_skus, base_prices)
            sku_indices_list.extend(day_sku_indices)

            # 计算类目指数
            day_category_indices = self._compute_category_indices(date_str, day_categories, day_sku_indices, day_skus)
            category_indices.extend(day_category_indices)

            # 计算全网指数
            day_overall = self._compute_overall_index(date_str, day_categories, day_category_indices, prev_overall)
            overall_indices.append(day_overall)
            prev_overall["overall"] = day_overall.index_val

            # 涨跌幅 TOP
            if len(day_sku_indices) > 1:
                top_movers.extend(self._compute_top_movers(date_str, day_sku_indices))

        logger = get_logger()
        logger.info(
            "Index computation complete: %d overall, %d category, %d sku indices, %d top movers",
            len(overall_indices), len(category_indices), len(sku_indices_list), len(top_movers)
        )
        return IndexResult(overall_indices, category_indices, sku_indices_list, top_movers)

    def _compute_base_prices(self, sku_summaries: List[SkuDailySummary]) -> Dict[str, float]:
        """计算基期均价"""
        return {
            s.sku_id: s.avg_price
            for s in sku_summaries
            if s.date == self.base_date
        }

    @staticmethod
    def _compute_sku_indices(date_str: str, sku_summaries: List[SkuDailySummary],
                             base_prices: Dict[str, float]) -> List[PriceIndex]:
        """SKU 指数 = (当日均价 / 基期均价) × 100"""
        indices: List[PriceIndex] = []
        for sku in sku_summaries:
            base = base_prices.get(sku.sku_id, sku.avg_price)
            index_value = (sku.avg_price / base * 100.0) if base > 0 else 100.0
            pi = PriceIndex(
                date=date_str, sku_id=sku.sku_id, product_name=sku.product_name,
                category=sku.category_l1, index_val=round(index_value, 2),
                change_pct=round(index_value - 100.0, 2)
            )
            indices.append(pi)
        return indices

    @staticmethod
    def _compute_category_indices(date_str: str, categories: List[CategoryDailySummary],
                                   sku_indices: List[PriceIndex],
                                   sku_summaries: List[SkuDailySummary]) -> List[PriceIndex]:
        """类目指数 = Σ(SKU指数 × SKU销量权重)
        SKU销量权重 = SKU销量 / 类目总销量
        """
        if not categories:
            return []

        # 按类目分组 SKU 指数
        sku_by_cat: Dict[str, List[PriceIndex]] = defaultdict(list)
        for si in sku_indices:
            if si.category:
                sku_by_cat[si.category].append(si)

        # SKU 销量映射
        sku_sales: Dict[str, int] = {s.sku_id: s.total_sales for s in sku_summaries}
        cat_sales: Dict[str, int] = {c.category_l1: c.total_sales for c in categories}

        indices: List[PriceIndex] = []
        for cat in categories:
            category = cat.category_l1
            cat_skus = sku_by_cat.get(category, [])
            if not cat_skus:
                continue

            # 按销量加权计算类目指数
            cat_total = float(cat_sales.get(category, 1))
            weighted = 0.0
            for si in cat_skus:
                sku_sale = float(sku_sales.get(si.sku_id, 0))
                weight = sku_sale / cat_total if cat_total > 0 else (1.0 / len(cat_skus))
                weighted += si.index_val * weight

            pi = PriceIndex(
                date=date_str, category=category,
                index_val=round(weighted, 2), change_pct=0.0
            )
            indices.append(pi)
        return indices

    @staticmethod
    def _compute_overall_index(date_str: str, categories: List[CategoryDailySummary],
                                category_indices: List[PriceIndex],
                                prev_overall: Dict[str, float]) -> PriceIndex:
        """全网指数 = Σ(类目指数 × 类目销量权重)"""
        if not categories:
            return PriceIndex(date=date_str, index_val=100.0, change_pct=0.0)

        cat_index_map = {ci.category: ci.index_val for ci in category_indices if ci.category}
        total_sales = sum(c.total_sales for c in categories)

        weighted = 0.0
        for cat in categories:
            ci = cat_index_map.get(cat.category_l1, 100.0)
            weight = (cat.total_sales / total_sales) if total_sales > 0 else 0
            weighted += ci * weight

        prev = prev_overall.get("overall", weighted)
        change_pct = ((weighted / prev) - 1.0) * 100.0 if prev > 0 else 0.0

        return PriceIndex(
            date=date_str, index_val=round(weighted, 2),
            change_pct=round(change_pct, 2)
        )

    @staticmethod
    def _compute_top_movers(date_str: str, sku_indices: List[PriceIndex]) -> List[PriceIndex]:
        """涨跌幅 TOP 20"""
        sorted_indices = sorted(sku_indices, key=lambda x: x.change_pct, reverse=True)
        return sorted_indices[:20]


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
