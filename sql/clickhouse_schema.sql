-- ClickHouse 价格指数平台完整建表语句

-- ==========================================
-- ODS 层：原始价格数据
-- ==========================================
CREATE TABLE IF NOT EXISTS ods_raw_prices (
    date Date COMMENT '日期',
    sku_id String COMMENT 'SKU ID',
    product_name String COMMENT '商品名称',
    category_l1 String COMMENT '一级类目',
    category_l2 String COMMENT '二级类目',
    brand String COMMENT '品牌',
    price Float64 COMMENT '价格',
    sales Int64 COMMENT '销量'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, sku_id);

-- ==========================================
-- DWD 层：清洗后数据
-- ==========================================
CREATE TABLE IF NOT EXISTS dwd_clean_prices (
    date Date COMMENT '日期',
    sku_id String COMMENT 'SKU ID',
    product_name String COMMENT '商品名称',
    category_l1 String COMMENT '一级类目',
    category_l2 String COMMENT '二级类目',
    brand String COMMENT '品牌',
    price Float64 COMMENT '价格',
    sales Int64 COMMENT '销量'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, sku_id);

-- ==========================================
-- DWS 层：SKU 日汇总
-- ==========================================
CREATE TABLE IF NOT EXISTS dws_sku_daily_summary (
    date Date COMMENT '日期',
    sku_id String COMMENT 'SKU ID',
    product_name String COMMENT '商品名称',
    category_l1 String COMMENT '一级类目',
    category_l2 String COMMENT '二级类目',
    brand String COMMENT '品牌',
    avg_price Float64 COMMENT '平均价格',
    total_sales Int64 COMMENT '总销量',
    record_count UInt32 COMMENT '记录数'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, sku_id);

-- ==========================================
-- DWS 层：类目日汇总
-- ==========================================
CREATE TABLE IF NOT EXISTS dws_category_daily_summary (
    date Date COMMENT '日期',
    category String COMMENT '类目',
    avg_price Float64 COMMENT '平均价格',
    total_sales Int64 COMMENT '总销量',
    sku_count UInt32 COMMENT 'SKU 数量'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, category);

-- ==========================================
-- DWS 层：全网日汇总
-- ==========================================
CREATE TABLE IF NOT EXISTS dws_overall_daily_summary (
    date Date COMMENT '日期',
    avg_price Float64 COMMENT '全网平均价格',
    total_sales Int64 COMMENT '全网总销量',
    total_skus UInt32 COMMENT 'SKU 总数',
    total_records UInt32 COMMENT '记录总数'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY date;

-- ==========================================
-- ADS 层：价格指数日报
-- ==========================================
CREATE TABLE IF NOT EXISTS ads_price_index_daily (
    date Date COMMENT '日期',
    index_type String COMMENT '类型: overall / category / sku',
    dimension_value String COMMENT '维度值',
    index_value Float64 COMMENT '指数值',
    change_pct Float64 COMMENT '环比涨跌幅(%)',
    base_value Float64 COMMENT '基期值'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, index_type, dimension_value);


-- ==========================================
-- 查询示例
-- ==========================================

-- 全网指数趋势
-- SELECT date, index_value, change_pct
-- FROM ads_price_index_daily
-- WHERE index_type = 'overall' ORDER BY date;

-- 类目指数排名
-- SELECT dimension_value, index_value, change_pct
-- FROM ads_price_index_daily
-- WHERE index_type = 'category' AND date = '2026-06-30'
-- ORDER BY change_pct DESC LIMIT 10;

-- 某类目下 SKU 销量排名
-- SELECT date, sku_id, product_name, avg_price, total_sales
-- FROM dws_sku_daily_summary
-- WHERE category_l1 = '手机数码' AND date = '2026-06-30'
-- ORDER BY total_sales DESC LIMIT 20;
