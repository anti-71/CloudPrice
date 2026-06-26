# Cloud Price Index

电商价格指数计算平台 —— 模拟商品价格数据的采集、清洗、汇总与指数计算。

## 项目概述

生成模拟电商价格数据，按照数仓分层架构（ODS → DWD → DWS → ADS）处理，最终输出价格指数报告（JSON/CSV）。支持本地存储与阿里云 OSS 两种方式。

## 技术栈

- Python 3.10+
- `oss2` - 阿里云 OSS SDK
- `pyyaml` - 配置解析
- `pytest` - 单元测试（标准库为主）

## 数据分层

```
ODS (原始数据层)  →  product_price_raw.csv
  ↓ 清洗
DWD (明细数据层)  →  product_price_clean.csv
  ↓ 汇总
DWS (汇总数据层)  →  sku / category / overall 日汇总
  ↓ 指数计算
ADS (应用数据层)  →  JSON 报告（指数、涨跌幅、日报）
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行（默认使用本地存储）
python src/main.py

# 指定日期范围
python src/main.py --start-date 2026-06-01 --end-date 2026-06-30
```

如需启用 OSS，配置 `.env` 文件（参见下方安全说明）。

## 项目结构

```
├── config/config.yaml         # 参数配置
├── src/
│   ├── main.py                # 主入口
│   ├── ingestion/             # 模拟数据生成
│   ├── compute/               # 清洗 → 汇总 → 指数计算
│   ├── storage/               # 本地 / OSS 存储
│   ├── report/                # 报告生成
│   └── util/                  # 工具函数
├── tests/                     # 单元测试
├── data/                      # 输出数据目录
├── sql/                       # ClickHouse 扩展方案
└── requirements.txt
```

## ⚠️ 安全提醒

- `.env` 文件包含阿里云 AccessKey，已加入 `.gitignore`
- 生产环境建议使用 RAM 角色而非 AccessKey
- 不要将任何密钥提交到版本控制

## 数据量

默认配置：30 天 × 2000 SKU × 3 平台，约 10-20 万行数据。
