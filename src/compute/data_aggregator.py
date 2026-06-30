"""数据汇总 — pandas 版本"""

import pandas as pd


class DataAggregator:

    def aggregate(self, df: pd.DataFrame) -> dict:
        """返回 {'sku': DataFrame, 'cat': DataFrame, 'ovr': DataFrame}"""
        sku = self.sku_daily(df)
        cat = self.category_daily(sku)
        ovr = self.overall_daily(sku)
        get_logger().info("Aggregation: %d sku, %d cat, %d overall", len(sku), len(cat), len(ovr))
        return {"sku": sku, "cat": cat, "ovr": ovr}

    def sku_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby(["date", "sku_id", "product_name", "category_l1", "category_l2", "brand"]).agg(
            avg_price=("price", "mean"), total_sales=("sales", "sum"),
            shop_count=("shop_id", "nunique"), record_count=("price", "count"),
            min_price=("price", "min"), max_price=("price", "max"),
        ).round({"avg_price": 2, "min_price": 2, "max_price": 2}).reset_index()

    def category_daily(self, sku: pd.DataFrame) -> pd.DataFrame:
        return sku.groupby(["date", "category_l1"]).agg(
            avg_price=("avg_price", "mean"), total_sales=("total_sales", "sum"),
            sku_count=("sku_id", "nunique"), record_count=("record_count", "sum"),
            min_price=("min_price", "min"), max_price=("max_price", "max"),
        ).round({"avg_price": 2}).reset_index().rename(columns={"category_l1": "category"})

    def overall_daily(self, sku: pd.DataFrame) -> pd.DataFrame:
        return sku.groupby("date").agg(
            avg_price=("avg_price", "mean"), total_sales=("total_sales", "sum"),
            total_skus=("sku_id", "nunique"), total_records=("record_count", "sum"),
            min_price=("min_price", "min"), max_price=("max_price", "max"),
        ).round({"avg_price": 2}).reset_index()


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
