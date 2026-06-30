"""CSV 数据导入 ClickHouse —— 支持 GB 级数据集"""

import os, sys, glob
import pandas as pd
from src.storage.clickhouse_client import ClickHouseClient
from src.util.config_loader import ConfigLoader

if os.getenv("CI"):
    print("CI runner: ClickHouse unreachable, skipping import")
    sys.exit(0)


def main():
    config = ConfigLoader()
    ch = ClickHouseClient(config)

    # 1. 建表
    print("Creating tables...")
    with open("sql/clickhouse_schema.sql", "r", encoding="utf-8") as f:
        for sql in f.read().split(";"):
            sql = sql.strip()
            if sql and not sql.startswith("--"):
                ch.execute(sql)
    print("Tables created.")

    # 2. 导入 ODS 数据
    import_ods(ch)

    # 3. 清洗 (ClickHouse SQL)
    run_cleaning(ch)

    # 4. 汇总 + 指数计算 (ClickHouse SQL)
    run_aggregation(ch)

    print("Done. Query results with: python query_clickhouse.py")


def import_ods(ch: ClickHouseClient):
    """从 OSS 路径批量导入 CSV 到 ClickHouse"""
    import glob
    csv_files = sorted(glob.glob("data/ods/*.csv"))
    if not csv_files:
        print("No ODS CSV files found. Run main.py first to generate data.")
        return

    for f in csv_files:
        print(f"Importing {f}...")
        df = pd.read_csv(f)
        # 批量插入
        rows = df.to_dict("records")
        for row in rows:
            row["date"] = str(row.get("date", ""))
            row["sku_id"] = str(row.get("sku_id", ""))
            row["product_name"] = str(row.get("product_name", ""))
            row["category_l1"] = str(row.get("category_l1", ""))
            row["category_l2"] = str(row.get("category_l2", ""))
            row["brand"] = str(row.get("brand", ""))
            row["price"] = float(row.get("price", 0))
            row["sales"] = int(row.get("sales", 0))

        # 用 INSERT VALUES 批量
        values = []
        for r in rows:
            values.append(
                f"('{r['date']}','{r['sku_id']}','{r['product_name']}','{r['category_l1']}',"
                f"'{r['category_l2']}','{r['brand']}',{r['price']},{r['sales']})"
            )
        ch.execute("INSERT INTO ods_raw_prices VALUES " + ",".join(values))
    print(f"Imported {len(csv_files)} files.")


def run_cleaning(ch: ClickHouseClient):
    ch.execute("""
        INSERT INTO dwd_clean_prices
        SELECT date, sku_id, product_name, category_l1, category_l2, brand, price, sales
        FROM ods_raw_prices
        WHERE price > 0 AND sales >= 0
          AND product_name IS NOT NULL AND product_name != ''
    """)
    print("Cleaning done.")


def run_aggregation(ch: ClickHouseClient):
    ch.execute("""
        INSERT INTO dws_sku_daily_summary
        SELECT date, sku_id, product_name, category_l1, category_l2, brand,
               avg(price) AS avg_price, sum(sales) AS total_sales, count() AS record_count
        FROM dwd_clean_prices
        GROUP BY date, sku_id, product_name, category_l1, category_l2, brand
    """)
    print("Aggregation done.")


if __name__ == "__main__":
    main()
