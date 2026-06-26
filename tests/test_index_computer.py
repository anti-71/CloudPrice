"""IndexComputer 单元测试"""

from src.compute.index_computer import IndexComputer
from src.models import (
    CategoryDailySummary, OverallDailySummary, PriceIndex, SkuDailySummary
)


def _make_sku(date: str, sku_id: str, category: str,
              avg_price: float, sales: int) -> SkuDailySummary:
    return SkuDailySummary(
        date=date, sku_id=sku_id, product_id=f"PROD{sku_id[4:]}",
        product_name=f"Test Product {sku_id}", category_l1=category,
        category_l2=category, brand="TestBrand", avg_price=avg_price,
        min_price=avg_price * 0.9, max_price=avg_price * 1.1,
        total_sales=sales, shop_count=3, record_count=3
    )


def _make_cat(date: str, category: str, avg_price: float,
              sales: int) -> CategoryDailySummary:
    return CategoryDailySummary(
        date=date, category_l1=category, category_l2=category,
        avg_price=avg_price, min_price=avg_price * 0.9,
        max_price=avg_price * 1.1, total_sales=sales, sku_count=1, record_count=1
    )


def _make_overall(date: str, avg_price: float, sales: int,
                  skus: int) -> OverallDailySummary:
    return OverallDailySummary(
        date=date, avg_price=avg_price, min_price=avg_price * 0.9,
        max_price=avg_price * 1.1, total_sales=sales, total_skus=skus,
        total_records=skus * 3
    )


def test_compute_with_empty_data():
    computer = IndexComputer("2026-06-01")
    result = computer.compute([], [], [])
    assert len(result.overall_indices) == 0
    assert len(result.category_indices) == 0
    assert len(result.sku_indices) == 0
    assert len(result.top_movers) == 0


def test_compute_sku_index():
    computer = IndexComputer("2026-06-01")
    skus = [
        _make_sku("2026-06-01", "SKU0001", "手机数码", 100.0, 500),
        _make_sku("2026-06-02", "SKU0001", "手机数码", 110.0, 600),
    ]
    cats = [
        _make_cat("2026-06-01", "手机数码", 100.0, 500),
        _make_cat("2026-06-02", "手机数码", 110.0, 600),
    ]
    overs = [
        _make_overall("2026-06-01", 100.0, 500, 1),
        _make_overall("2026-06-02", 110.0, 600, 1),
    ]

    result = computer.compute(skus, cats, overs)
    assert len(result.overall_indices) == 2
    assert len(result.sku_indices) == 2

    # 基期指数应为 100
    base = [i for i in result.sku_indices if i.date == "2026-06-01"][0]
    assert abs(base.index_val - 100.0) < 0.01

    # 第二天指数 = 110
    day2 = [i for i in result.sku_indices if i.date == "2026-06-02"][0]
    assert abs(day2.index_val - 110.0) < 0.01


def test_compute_overall_index():
    computer = IndexComputer("2026-06-01")
    skus = [
        _make_sku("2026-06-01", "SKU0001", "手机数码", 100.0, 500),
        _make_sku("2026-06-01", "SKU0002", "电脑办公", 200.0, 300),
        _make_sku("2026-06-02", "SKU0001", "手机数码", 110.0, 600),
        _make_sku("2026-06-02", "SKU0002", "电脑办公", 190.0, 350),
    ]
    cats = [
        _make_cat("2026-06-01", "手机数码", 100.0, 500),
        _make_cat("2026-06-01", "电脑办公", 200.0, 300),
        _make_cat("2026-06-02", "手机数码", 110.0, 600),
        _make_cat("2026-06-02", "电脑办公", 190.0, 350),
    ]
    overs = [
        _make_overall("2026-06-01", 150.0, 800, 2),
        _make_overall("2026-06-02", 145.0, 950, 2),
    ]

    result = computer.compute(skus, cats, overs)
    base = [i for i in result.overall_indices if i.date == "2026-06-01"][0]
    assert abs(base.index_val - 100.0) < 0.01


def test_null_inputs():
    computer = IndexComputer("2026-06-01")
    result = computer.compute(None, None, None)
    assert len(result.overall_indices) == 0
