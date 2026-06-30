"""价格指数计算 — pandas 版本"""

import pandas as pd


class IndexComputer:

    def __init__(self, base_date: str):
        self.base_date = base_date

    def compute(self, sku: pd.DataFrame, cat: pd.DataFrame, ovr: pd.DataFrame) -> dict:
        """返回 {'overall': DataFrame, 'category': DataFrame, 'sku': DataFrame, 'top': DataFrame}"""
        if len(sku) == 0:
            empty = pd.DataFrame()
            return {"overall": empty, "category": empty, "sku": empty, "top": empty}
        si = self.sku_index(sku)
        ci = self.category_index(si, cat)
        oi = self.overall_index(ci, cat)
        top = self.top_movers(si)
        return {"overall": oi, "category": ci, "sku": si, "top": top}

    def sku_index(self, sku: pd.DataFrame) -> pd.DataFrame:
        if sku is None or len(sku) == 0:
            return pd.DataFrame()
        base = sku[sku["date"] == self.base_date][["sku_id", "avg_price"]].rename(columns={"avg_price": "base_price"})
        df = sku.merge(base, on="sku_id", how="left")
        df["index"] = (df["avg_price"] / df["base_price"] * 100).round(2)
        df = df.sort_values(["sku_id", "date"])
        df["prev"] = df.groupby("sku_id")["index"].shift(1)
        df["change_pct"] = ((df["index"] / df["prev"] - 1) * 100).round(2).fillna(0)
        return df

    def category_index(self, si: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
        if si is None or len(si) == 0:
            return pd.DataFrame()
        si = si.copy()
        si["weight"] = si.groupby(["date", "category_l1"])["total_sales"].transform(lambda x: x / x.sum())
        ci = si.groupby(["date", "category_l1"]).apply(lambda g: (g["index"] * g["weight"]).sum(), include_groups=False).reset_index()
        ci.columns = ["date", "category", "index"]
        ci["index"] = ci["index"].round(2)
        ci = ci.sort_values(["category", "date"])
        ci["prev"] = ci.groupby("category")["index"].shift(1)
        ci["change_pct"] = ((ci["index"] / ci["prev"] - 1) * 100).round(2).fillna(0)
        return ci

    def overall_index(self, ci: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
        if ci is None or len(ci) == 0:
            return pd.DataFrame()
        merged = ci.merge(cat[["date", "category", "total_sales"]], on=["date", "category"], how="left")
        merged["weight"] = merged.groupby("date")["total_sales"].transform(lambda x: x / x.sum())
        oi = merged.groupby("date").apply(lambda g: (g["index"] * g["weight"]).sum(), include_groups=False).reset_index()
        oi.columns = ["date", "index"]
        oi["index"] = oi["index"].round(2)
        oi = oi.sort_values("date")
        oi["prev"] = oi["index"].shift(1)
        oi["change_pct"] = ((oi["index"] / oi["prev"] - 1) * 100).round(2).fillna(0)
        return oi

    def top_movers(self, si: pd.DataFrame, n: int = 50) -> pd.DataFrame:
        if si is None or len(si) == 0 or "date" not in si.columns:
            return pd.DataFrame()
        df = si[si["date"] != self.base_date].dropna(subset=["change_pct"])
        top = df.sort_values("change_pct", ascending=False).groupby("date").head(n // 2)
        bot = df.sort_values("change_pct", ascending=True).groupby("date").head(n // 2)
        return pd.concat([top, bot]).sort_values(["date", "change_pct"], ascending=[True, False])
