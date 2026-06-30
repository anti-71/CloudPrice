"""价格指数计算单元测试 — pandas 版本"""
import pandas as pd
import pytest
from src.compute.index_computer import IndexComputer


def _sku_df(dates_values: list):
    rows = []
    for d, v in dates_values:
        rows.append({"date": d, "sku_id": "SKU0001", "product_name": "p", "category_l1": "c1",
                      "category_l2": "c2", "brand": "b", "avg_price": v, "total_sales": 100,
                      "shop_count": 3, "record_count": 5, "min_price": v, "max_price": v})
    return pd.DataFrame(rows)

def _cat_df(dates_values: list):
    rows = []
    for d, v in dates_values:
        rows.append({"date": d, "category": "c1", "avg_price": v, "total_sales": 100,
                      "sku_count": 1, "record_count": 5, "min_price": v, "max_price": v})
    return pd.DataFrame(rows)

def _ovr_df(dates_values: list):
    rows = []
    for d, v in dates_values:
        rows.append({"date": d, "avg_price": v, "total_sales": 100,
                      "total_skus": 1, "total_records": 5, "min_price": v, "max_price": v})
    return pd.DataFrame(rows)


class TestIndexComputer:

    def test_base_is_100(self):
        ic = IndexComputer("2023-06-01")
        sku = _sku_df([("2023-06-01", 50.0)])
        cat = _cat_df([("2023-06-01", 50.0)])
        ovr = _ovr_df([("2023-06-01", 50.0)])
        r = ic.compute(sku, cat, ovr)
        assert r["overall"]["index"].iloc[0] == 100.0

    def test_price_double_index_double(self):
        ic = IndexComputer("2023-06-01")
        sku = _sku_df([("2023-06-01", 50.0), ("2023-06-02", 100.0)])
        cat = _cat_df([("2023-06-01", 50.0), ("2023-06-02", 100.0)])
        ovr = _ovr_df([("2023-06-01", 50.0), ("2023-06-02", 100.0)])
        r = ic.compute(sku, cat, ovr)
        assert abs(r["overall"]["index"].iloc[1] - 200.0) < 1

    def test_change_pct(self):
        ic = IndexComputer("2023-06-01")
        sku = _sku_df([("2023-06-01", 100.0), ("2023-06-02", 150.0)])
        cat = _cat_df([("2023-06-01", 100.0), ("2023-06-02", 150.0)])
        ovr = _ovr_df([("2023-06-01", 100.0), ("2023-06-02", 150.0)])
        r = ic.compute(sku, cat, ovr)
        assert abs(r["overall"]["change_pct"].iloc[1] - 50.0) < 1

    def test_empty_passes(self):
        ic = IndexComputer("2023-06-01")
        empty = pd.DataFrame({"date": [], "sku_id": [], "avg_price": [], "total_sales": [],
                              "category": [], "category_l1": []})
        r = ic.compute(empty, empty, empty)
        assert len(r["overall"]) == 0
        assert len(r["category"]) == 0
