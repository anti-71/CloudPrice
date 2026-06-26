"""报告生成器

聚合 ADS 层各指数，生成每日报告 JSON
"""

import json
from typing import Dict, List

from src.models import OverallDailySummary, PriceIndex


class ReportGenerator:
    """报告生成器"""

    def generate_daily_report(self, overall_indices: List[PriceIndex],
                               overall_summaries: List[OverallDailySummary]) -> str:
        """生成每日报告 JSON"""
        summary_map: Dict[str, OverallDailySummary] = {
            s.date: s for s in overall_summaries
        }

        report: List[Dict] = []
        for idx in overall_indices:
            s = summary_map.get(idx.date)
            report.append({
                "date": idx.date,
                "overallIndex": idx.index_val,
                "changePct": idx.change_pct,
                "totalSkus": s.total_skus if s else 0,
                "totalSales": s.total_sales if s else 0,
                "avgPrice": s.avg_price if s else 0.0,
            })

        result = json.dumps(report, ensure_ascii=False, indent=2)
        get_logger().info("Generated daily report with %d entries", len(report))
        return result

    def to_json(self, items: List) -> str:
        """将对象列表序列化为 JSON 字符串"""
        data = []
        for item in items:
            if hasattr(item, 'to_dict'):
                data.append(item.to_dict())
            elif hasattr(item, '__dict__'):
                data.append(item.__dict__)
            else:
                data.append(item)
        return json.dumps(data, ensure_ascii=False, indent=2)


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
