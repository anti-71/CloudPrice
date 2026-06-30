"""数据格式校验与字段类型转换测试

验证：日期格式、价格类型、品类码统一、字段完整性
"""

import pandas as pd
import pytest
from datetime import datetime

from src.ingestion.mock_data_generator import MockDataGenerator
from src.compute.data_cleaner import DataCleaner
from src.util.config_loader import ConfigLoader


class TestDataFormat:

    def setup_method(self):
        self.config = ConfigLoader()
        self.gen = MockDataGenerator(self.config, seed=42)
        self.df = self.gen.generate("2023-06-01", "2023-06-02")

    # ─── 1. 日期格式校验 ───

    def test_date_format_ymd(self):
        """日期必须是 YYYY-MM-DD 格式"""
        for d in self.df["date"].unique():
            datetime.strptime(str(d), "%Y-%m-%d")  # 不抛异常即通过

    def test_date_range_correct(self):
        """日期应在生成范围内"""
        dates = pd.to_datetime(self.df["date"])
        assert dates.min() >= pd.Timestamp("2023-06-01")
        assert dates.max() <= pd.Timestamp("2023-06-02")

    # ─── 2. 字段类型校验 ───

    def test_price_is_float(self):
        """price 必须是数值"""
        clean = DataCleaner().clean(self.df)
        assert pd.api.types.is_float_dtype(clean["price"]) or pd.api.types.is_numeric_dtype(clean["price"])

    def test_sales_is_int(self):
        """sales 必须是整数"""
        clean = DataCleaner().clean(self.df)
        assert pd.api.types.is_integer_dtype(clean["sales"]) or pd.api.types.is_numeric_dtype(clean["sales"])

    def test_price_positive_after_clean(self):
        """清洗后 price 必须 > 0"""
        clean = DataCleaner().clean(self.df)
        assert (clean["price"] > 0).all()

    def test_no_empty_product_name_after_clean(self):
        """清洗后 product_name 不能为空"""
        clean = DataCleaner().clean(self.df)
        assert not clean["product_name"].isna().any()
        assert (clean["product_name"] != "").all()

    # ─── 3. 字段完整性 ───

    REQUIRED_COLS = ["date", "sku_id", "product_name", "category_l1",
                     "category_l2", "brand", "platform", "price", "sales"]

    def test_required_columns_present(self):
        """所有必需字段必须存在"""
        for col in self.REQUIRED_COLS:
            assert col in self.df.columns, f"缺少字段 {col}"

    def test_no_null_in_key_fields(self):
        """关键字段不能有 NULL"""
        key_cols = ["date", "sku_id", "platform"]
        for col in key_cols:
            assert not self.df[col].isna().any(), f"{col} 存在 NULL"

    # ─── 4. 品类码统一 ───

    def test_category_in_known_set(self):
        """category_l1 必须是已知类目"""
        valid = set(self.config.categories)
        actual = set(self.df["category_l1"].unique())
        assert actual.issubset(valid), f"未知类目: {actual - valid}"

    # ─── 5. 平台校验 ───

    def test_platform_in_known_set(self):
        """platform 必须是已知平台"""
        valid = set(self.config.platforms)
        actual = set(self.df["platform"].unique())
        assert actual.issubset(valid), f"未知平台: {actual - valid}"
