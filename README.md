# Cloud Price Index - 基于阿里云 OSS 与 DataV 的高频电商价格指数计算平台

## 项目背景

本项目是一个轻量级云端数据处理原型，模拟电商商品价格数据的采集、清洗、汇总和指数计算流程。系统生成模拟的电商价格数据，按照数仓分层架构进行处理，最终生成可供 DataV 可视化的价格指数报告。

## 技术架构

### 技术栈
- Python 3.10+
- `csv` - CSV 文件读写（标准库）
- `json` - JSON 序列化/反序列化（标准库）
- `oss2` - 阿里云 OSS Python SDK
- `pyyaml` - YAML 配置文件解析
- `dataclasses` - 数据类（标准库）
- `logging` - 日志记录（标准库）
- `argparse` - 命令行参数解析（标准库）
- `pytest` - 单元测试

### 数据分层架构

```
ODS (Operational Data Store) - 原始数据层
  ↓ 清洗
DWD (Data Warehouse Detail) - 明细数据层
  ↓ 汇总
DWS (Data Warehouse Summary) - 汇总数据层
  ↓ 计算指数
ADS (Application Data Service) - 应用数据层
```

#### 1. ODS 层
- **product_price_raw.csv**: 原始模拟商品价格数据
- 字段：date, sku_id, product_id, product_name, category_l1, category_l2, brand, platform, shop_id, price, sales, is_promo, collect_time

#### 2. DWD 层
- **product_price_clean.csv**: 清洗后的商品价格明细
- 清洗规则：
  - 删除 price <= 0 的记录
  - 删除 sales < 0 的记录
  - 删除商品名称为空的记录
  - 删除价格异常暴涨（10倍以上）的记录
  - 去除重复报价

#### 3. DWS 层
- **sku_daily_summary.csv**: SKU 日汇总
- **category_daily_summary.csv**: 类目日汇总
- **overall_daily_summary.csv**: 全网日汇总

#### 4. ADS 层
- **overall_index.json**: 全网价格指数时间序列
- **category_index.json**: 各类目价格指数
- **sku_index.json**: TOP SKU 价格指数
- **top_movers.json**: 涨跌幅 TOP 商品
- **daily_report.json**: 每日数据报告

## 价格指数计算方法

### 基本公式
- **SKU 指数** = (当日均价 / 基期均价) × 100
- **类目指数** = Σ(SKU指数 × SKU销量权重)
- **全网指数** = Σ(类目指数 × 类目销量权重)
- **环比涨跌幅** = (当日指数 / 前一日指数) - 1

### 权重计算
- SKU 销量权重 = SKU销量 / 类目总销量
- 类目销量权重 = 类目销量 / 全网总销量

## 项目结构

```
cloud-price-index/
├── README.md                        # 项目说明
├── requirements.txt                 # Python 依赖
├── .env.example                     # 环境变量示例
├── config/
│   └── config.yaml                  # 项目配置
├── src/
│   ├── __init__.py
│   ├── main.py                      # 主入口
│   ├── models.py                    # 数据模型（dataclass）
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── mock_data_generator.py   # 模拟数据生成
│   ├── compute/
│   │   ├── __init__.py
│   │   ├── data_cleaner.py          # 数据清洗
│   │   ├── data_aggregator.py       # 数据汇总
│   │   └── index_computer.py        # 指数计算
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── local_storage.py         # 本地存储
│   │   └── oss_client.py            # OSS 客户端
│   ├── report/
│   │   ├── __init__.py
│   │   └── report_generator.py      # 报告生成
│   └── util/
│       ├── __init__.py
│       ├── date_utils.py            # 日期工具
│       ├── config_loader.py         # 配置加载
│       └── logger_config.py         # 日志配置
├── tests/
│   ├── __init__.py
│   └── test_index_computer.py       # 单元测试
├── sql/
│   └── clickhouse_schema.sql        # ClickHouse 扩展方案
├── data/                            # 本地数据目录
│   ├── ods/
│   ├── dwd/
│   ├── dws/
│   └── ads/
└── logs/                            # 日志目录
```

## 快速开始

### 1. 环境要求

- Python 3.10+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，并根据需要配置：

```env
# 是否启用 OSS（false 表示只保存到本地）
OSS_ENABLED=false

# 阿里云 OSS 配置（OSS_ENABLED=true 时需要）
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_BUCKET=your-bucket-name
ALIYUN_ACCESS_KEY_ID=your-access-key-id
ALIYUN_ACCESS_KEY_SECRET=your-access-key-secret
OSS_PREFIX=price-index-platform
```

### 4. 修改配置文件（可选）

编辑 `config/config.yaml` 调整数据生成参数：

```yaml
project-name: cloud-price-index
base-date: "2026-06-01"
start-date: "2026-06-01"
end-date: "2026-06-30"
sku-count: 2000
platforms: ["淘宝", "京东", "拼多多"]
categories: ["手机数码", "电脑办公", "家用电器", "食品饮料", "服饰鞋包", "美妆个护", "运动户外", "日用百货"]
dirty-data-rate: 0.02
```

### 5. 运行

```bash
# 生成整个时间段的数据（从配置文件读取日期范围）
python src/main.py

# 指定单个日期
python src/main.py --date 2026-06-21

# 指定日期范围
python src/main.py --start-date 2026-06-01 --end-date 2026-06-30
```

## OSS 存储路径

当 `OSS_ENABLED=true` 时，数据会上传到以下路径：

```
price-index-platform/
├── ods/product_price_raw/dt=YYYY-MM-DD/product_price_raw.csv
├── dwd/product_price_clean/dt=YYYY-MM-DD/product_price_clean.csv
├── dws/sku_daily_summary/dt=YYYY-MM-DD/sku_daily_summary.csv
├── dws/category_daily_summary/dt=YYYY-MM-DD/category_daily_summary.csv
├── dws/overall_daily_summary/dt=YYYY-MM-DD/overall_daily_summary.csv
└── ads/
    ├── overall_index.json
    ├── category_index.json
    ├── sku_index.json
    ├── top_movers.json
    └── daily_report.json
```

## DataV 对接

### 数据源配置

1. 在 DataV 中添加**阿里云 OSS 数据源**
2. 配置 Bucket 和访问凭证
3. 在组件中选择对应的 JSON 文件

### JSON 数据格式

#### overall_index.json - 全网价格指数
```json
[
  {
    "date": "2026-06-01",
    "index": 100.0,
    "changePct": 0.0
  }
]
```

> **注**: Python 侧直接输出驼峰命名字段；如 DataV 需要下划线字段名，可修改序列化逻辑使用 `snake_case`。

#### category_index.json - 类目价格指数
```json
[
  {
    "date": "2026-06-01",
    "category": "手机数码",
    "index": 100.0,
    "changePct": 0.0
  }
]
```

#### sku_index.json - TOP SKU 价格指数
```json
[
  {
    "date": "2026-06-01",
    "skuId": "SKU001",
    "productName": "iPhone 15 Pro",
    "category": "手机数码",
    "index": 100.0
  }
]
```

#### top_movers.json - 涨跌幅 TOP
```json
[
  {
    "date": "2026-06-02",
    "skuId": "SKU001",
    "productName": "iPhone 15 Pro",
    "category": "手机数码",
    "changePct": 5.2
  }
]
```

#### daily_report.json - 每日报告
```json
[
  {
    "date": "2026-06-01",
    "overallIndex": 100.0,
    "totalSkus": 2000,
    "totalSales": 150000,
    "avgPrice": 259.8
  }
]
```

## ClickHouse 扩展方案

项目提供了 ClickHouse 建表语句（`sql/clickhouse_schema.sql`），支持将数据导入 ClickHouse 进行更高性能的查询分析。

主要表：
- `raw_product_price_detail` - 原始价格明细
- `dws_sku_daily_summary` - SKU 日汇总
- `dws_category_daily_summary` - 类目日汇总
- `ads_price_index_daily` - 价格指数日报

## 数据量说明

默认配置下：
- 时间范围：30 天
- SKU 数量：2000 个
- 平台数量：3 个
- 每个 SKU 多店铺报价：2-5 个店铺
- 数据总量：约 10-20 万行

## 业务逻辑

### 价格波动规律
- 日常价格：基准价格 ± 5% 随机波动
- 促销日：价格下降 10-30%，销量提升 2-5 倍
- 周末效应：销量略有提升

### 脏数据模拟
- price <= 0
- sales < 0
- 商品名称为空
- 价格暴涨 10 倍以上
- 重复报价（相同 SKU、平台、店铺、日期）

脏数据比例默认 2%，可在配置文件中调整。

## 核心模块说明

| 模块 | 职责 |
|------|------|
| `main.py` | 主入口，解析命令行参数，编排各处理阶段 |
| `mock_data_generator.py` | 生成模拟价格数据，按 dirty-data-rate 注入脏数据 |
| `data_cleaner.py` | 清洗 ODS 层数据，输出 DWD 层 |
| `data_aggregator.py` | 汇总 DWD 层明细，输出 DWS 层日汇总 |
| `index_computer.py` | 基于 DWS 层计算各类指数，输出 ADS 层 JSON |
| `report_generator.py` | 聚合 ADS 层各指数，生成每日报告 JSON |
| `oss_client.py` | 封装阿里云 OSS Python SDK，支持上传 |
| `local_storage.py` | 本地 CSV/JSON 文件读写 |
| `config_loader.py` | 从 config.yaml 加载配置，支持环境变量覆盖 |

## 课程报告要点

1. **数据仓库分层架构**：ODS → DWD → DWS → ADS
2. **数据清洗规则**：如何识别和处理脏数据
3. **价格指数算法**：加权平均法、基期选择
4. **云存储方案**：OSS 的使用、分区策略
5. **可视化对接**：JSON 格式设计、DataV 配置

## 安全注意事项

- ⚠️ 不要将 `.env` 文件提交到版本控制
- ⚠️ 不要在代码中硬编码 AccessKey
- ⚠️ OSS Bucket 建议设置访问权限控制
- ⚠️ 生产环境建议使用 RAM 角色而非 AccessKey

## 许可证

MIT License
