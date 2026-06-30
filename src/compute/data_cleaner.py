"""数据清洗 — pandas 版本"""

import pandas as pd


class DataCleaner:

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)
        df = df[df["price"] > 0]
        df = df[df["sales"] >= 0]
        df = df[df["product_name"].notna() & (df["product_name"] != "")]
        median = df.groupby("sku_id")["price"].transform("median")
        df = df[df["price"] <= median * 10]
        df = df.drop_duplicates(subset=["date", "sku_id", "platform", "shop_id"], keep="first")
        df = df.reset_index(drop=True)
        get_logger().info("Cleaning: %d → %d (removed %d)", before, len(df), before - len(df))
        return df


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
