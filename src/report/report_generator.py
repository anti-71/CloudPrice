"""报告生成器

聚合 ADS 层各指数，生成每日报告 JSON
"""

import json
from typing import Dict, List

from src.models import OverallDailySummary, PriceIndex


class ReportGenerator:
    """报告生成器"""

    def generate_daily_report(self, overall_indices, overall_summaries) -> str:
        """生成每日报告 JSON（兼容旧版）"""
        return self.generate_daily_report_df(overall_indices, overall_summaries)

    def to_json(self, items) -> str:
        """序列化为 JSON"""
        import json
        if hasattr(items, "to_dict"):
            return json.dumps(items.to_dict("records"), ensure_ascii=False, indent=2)
        data = [item.to_dict() if hasattr(item, "to_dict") else item for item in items]
        return json.dumps(data, ensure_ascii=False, indent=2)

    # ── pandas DataFrame 版本 ──

    def to_json_df(self, df, key_col: str, cols=None):
        """DataFrame → JSON（按 key_col 分组）"""
        import json
        if cols:
            records = df[cols + [key_col]].to_dict("records")
        else:
            records = df.to_dict("records")
        return json.dumps(records, ensure_ascii=False, indent=2)

    def generate_daily_report_df(self, overall_df, ovr_df) -> str:
        """DataFrame 版本每日报告"""
        import json
        import pandas as pd
        merged = overall_df.merge(ovr_df[["date", "total_sales", "total_skus", "avg_price"]], on="date", how="left")
        report = []
        for _, r in merged.iterrows():
            report.append({
                "date": str(r["date"]),
                "overallIndex": float(r["index"]),
                "changePct": float(r.get("change_pct", 0)),
                "totalSkus": int(r.get("total_skus", 0)),
                "totalSales": int(r.get("total_sales", 0)),
                "avgPrice": float(r.get("avg_price", 0)),
            })
        result = json.dumps(report, ensure_ascii=False, indent=2)
        get_logger().info("Generated daily report with %d entries", len(report))
        return result


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
