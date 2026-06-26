-- ClickHouse 扩展方案
-- 支持将数据导入 ClickHouse 进行更高性能的查询分析

-- 1. 原始价格明细表 (ODS)
CREATE TABLE IF NOT EXISTS raw_product_price_detail (
    date Date,
    sku_id String,
    product_id String,
    product_name String,
    category_l1 String,
    category_l2 String,
    brand String,
    platform String,
    shop_id String,
    price Decimal(10, 2),
    sales UInt64,
    is_promo UInt8,
    collect_time DateTime,
    etl_time DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, sku_id, platform, shop_id);

-- 2. SKU 日汇总表 (DWS)
CREATE TABLE IF NOT EXISTS dws_sku_daily_summary (
    date Date,
    sku_id String,
    product_id String,
    product_name String,
    category_l1 String,
    category_l2 String,
    brand String,
    avg_price Decimal(10, 2),
    min_price Decimal(10, 2),
    max_price Decimal(10, 2),
    total_sales UInt64,
    shop_count UInt32,
    record_count UInt32,
    etl_time DateTime DEFAULT now()
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, sku_id);

-- 3. 类目日汇总表 (DWS)
CREATE TABLE IF NOT EXISTS dws_category_daily_summary (
    date Date,
    category_l1 String,
    category_l2 String,
    avg_price Decimal(10, 2),
    min_price Decimal(10, 2),
    max_price Decimal(10, 2),
    total_sales UInt64,
    sku_count UInt32,
    record_count UInt32,
    etl_time DateTime DEFAULT now()
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, category_l1, category_l2);

-- 4. 价格指数日报表 (ADS)
CREATE TABLE IF NOT EXISTS ads_price_index_daily (
    date Date,
    overall_index Float64,
    overall_change_pct Float64,
    category String,
    category_index Float64,
    category_change_pct Float64,
    sku_id String,
    sku_index Float64,
    sku_change_pct Float64,
    etl_time DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, category, sku_id);

-- 导入示例（从本地 CSV 导入）：
-- clickhouse-client --query="INSERT INTO raw_product_price_detail FORMAT CSV" < data/ods/product_price_raw.csv
