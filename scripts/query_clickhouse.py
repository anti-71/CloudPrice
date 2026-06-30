"""查询 ClickHouse 中的价格指数结果"""
import sys
from src.storage.clickhouse_client import ClickHouseClient
from src.util.config_loader import ConfigLoader

ch = ClickHouseClient(ConfigLoader())

queries = {
    "overview": """
        SELECT date, avg_price, total_sales, total_skus, total_records
        FROM dws_overall_daily_summary
        ORDER BY date LIMIT 10
    """,
    "category": """
        SELECT date, category, avg_price, total_sales
        FROM dws_category_daily_summary
        ORDER BY date, category LIMIT 10
    """,
    "top_sku": """
        SELECT date, sku_id, product_name, avg_price, total_sales
        FROM dws_sku_daily_summary
        ORDER BY total_sales DESC LIMIT 10
    """,
    "tables": "SHOW TABLES",
}

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "overview"
    if q in queries:
        print(ch.query(queries[q]))
    else:
        print("Available: " + ", ".join(queries.keys()))
