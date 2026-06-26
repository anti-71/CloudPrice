#!/usr/bin/env python3
"""
Cloud Price Index 主入口

基于阿里云 OSS 的高频电商价格指数计算平台

数据分层：ODS → DWD → DWS → ADS

命令行参数：
  --date YYYY-MM-DD        指定单个日期
  --start-date YYYY-MM-DD  指定开始日期
  --end-date YYYY-MM-DD    指定结束日期
  无参数                   从配置文件读取日期范围

所有数据直接上传 OSS，不写本地磁盘。
"""

import argparse
import csv
import io
import sys
from collections import defaultdict
from typing import List

from src.compute.data_aggregator import DataAggregator
from src.compute.data_cleaner import DataCleaner
from src.compute.index_computer import IndexComputer
from src.ingestion.mock_data_generator import MockDataGenerator
from src.models import (
    CategoryDailySummary, CleanPriceRecord, OverallDailySummary,
    RawPriceRecord, SkuDailySummary
)
from src.report.report_generator import ReportGenerator
from src.storage.oss_client import OssClient
from src.util.config_loader import ConfigLoader
from src.util.logger_config import setup_logger


def main():
    logger = setup_logger("cloud_price_index")

    logger.info("=" * 40)
    logger.info("  Cloud Price Index - Starting...")
    logger.info("  All data will be uploaded to OSS directly")
    logger.info("=" * 40)

    try:
        config = ConfigLoader()
        logger.info(
            "Config loaded: project=%s, skuCount=%d, dirtyRate=%.2f",
            config.project_name, config.sku_count, config.dirty_data_rate
        )

        if not config.oss_enabled:
            logger.error("OSS_ENABLED is not set to true. OSS is required.")
            sys.exit(1)

        parser = argparse.ArgumentParser(description="Cloud Price Index")
        parser.add_argument("--date", help="指定单个日期 (YYYY-MM-DD)")
        parser.add_argument("--start-date", help="指定开始日期 (YYYY-MM-DD)")
        parser.add_argument("--end-date", help="指定结束日期 (YYYY-MM-DD)")
        args = parser.parse_args()

        if args.date:
            start_date = end_date = args.date
        elif args.start_date or args.end_date:
            start_date = args.start_date or config.start_date
            end_date = args.end_date or config.end_date
        else:
            start_date = config.start_date
            end_date = config.end_date

        logger.info("Date range: %s to %s", start_date, end_date)

        ossClient = OssClient(config)
        generator = MockDataGenerator(config)
        cleaner = DataCleaner()
        aggregator = DataAggregator()
        indexComputer = IndexComputer(config.base_date)
        reportGenerator = ReportGenerator()

        # ========== 1. ODS 层 ==========
        logger.info("--- ODS Layer: Generating raw data ---")
        rawRecords = generator.generate(start_date, end_date)
        save_raw_to_oss(ossClient, config, rawRecords)

        # ========== 2. DWD 层 ==========
        logger.info("--- DWD Layer: Cleaning data ---")
        cleanRecords = cleaner.clean(rawRecords)
        save_clean_to_oss(ossClient, config, cleanRecords)

        # ========== 3. DWS 层 ==========
        logger.info("--- DWS Layer: Aggregating data ---")
        aggregation = aggregator.aggregate(cleanRecords)
        save_sku_to_oss(ossClient, config, aggregation.sku_summaries)
        save_category_to_oss(ossClient, config, aggregation.category_summaries)
        save_overall_to_oss(ossClient, config, aggregation.overall_summaries)

        # ========== 4. ADS 层 ==========
        logger.info("--- ADS Layer: Computing price indices ---")
        indices = indexComputer.compute(
            aggregation.sku_summaries,
            aggregation.category_summaries,
            aggregation.overall_summaries
        )
        save_ads_to_oss(ossClient, config, indices,
                        aggregation.overall_summaries, reportGenerator)

        logger.info("=" * 40)
        logger.info("  Cloud Price Index - Completed!")
        logger.info("  ODS: %d raw records", len(rawRecords))
        logger.info("  DWD: %d clean records", len(cleanRecords))
        logger.info("  DWS: %d sku, %d category, %d overall summaries",
                     len(aggregation.sku_summaries),
                     len(aggregation.category_summaries),
                     len(aggregation.overall_summaries))
        logger.info("  ADS: %d overall, %d category, %d sku indices",
                     len(indices.overall_indices),
                     len(indices.category_indices),
                     len(indices.sku_indices))
        logger.info("=" * 40)

    except Exception as e:
        logger.error("Application failed", exc_info=e)
        sys.exit(1)


# ========== ODS 层 OSS 上传 ==========

def save_raw_to_oss(ossClient, config, records):
    by_date = defaultdict(list)
    for r in records:
        by_date[r.date].append(r)

    for date_str, day_records in by_date.items():
        csv_content = to_raw_csv(day_records)
        filename = "product_price_raw.csv"
        ossClient.upload_string(
            ossClient.build_key("ods", f"dt={date_str}", filename),
            csv_content
        )

    get_logger().info("Uploaded %d raw records to ODS layer", len(records))


def to_raw_csv(records):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "sku_id", "product_id", "product_name", "category_l1",
                     "category_l2", "brand", "platform", "shop_id", "price",
                     "sales", "is_promo", "collect_time"])
    for r in records:
        writer.writerow([
            r.date, r.sku_id, r.product_id, r.product_name,
            r.category_l1, r.category_l2, r.brand, r.platform,
            r.shop_id, r.price, r.sales, r.is_promo, r.collect_time
        ])
    return output.getvalue()


# ========== DWD 层 OSS 上传 ==========

def save_clean_to_oss(ossClient, config, records):
    by_date = defaultdict(list)
    for r in records:
        by_date[r.date].append(r)

    for date_str, day_records in by_date.items():
        csv_content = to_clean_csv(day_records)
        filename = "product_price_clean.csv"
        ossClient.upload_string(
            ossClient.build_key("dwd", f"dt={date_str}", filename),
            csv_content
        )

    get_logger().info("Uploaded %d clean records to DWD layer", len(records))


def to_clean_csv(records):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "sku_id", "product_id", "product_name", "category_l1",
                     "category_l2", "brand", "platform", "shop_id", "price",
                     "sales", "is_promo", "collect_time"])
    for r in records:
        writer.writerow([
            r.date, r.sku_id, r.product_id, r.product_name,
            r.category_l1, r.category_l2, r.brand, r.platform,
            r.shop_id, r.price, r.sales, r.is_promo, r.collect_time
        ])
    return output.getvalue()


# ========== DWS 层 OSS 上传 ==========

def save_sku_to_oss(ossClient, config, summaries):
    filename = "sku_daily_summary.csv"
    by_date = defaultdict(list)
    for s in summaries:
        by_date[s.date].append(s)
    for dt, day_summaries in sorted(by_date.items()):
        day_csv = to_sku_summary_csv(day_summaries)
        ossClient.upload_string(
            ossClient.build_key("dws", f"dt={dt}", filename), day_csv
        )
    get_logger().info("Uploaded %d SKU summaries to DWS layer", len(summaries))


def to_sku_summary_csv(summaries):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "sku_id", "product_id", "product_name", "category_l1",
                     "category_l2", "brand", "avg_price", "min_price", "max_price",
                     "total_sales", "shop_count", "record_count"])
    for s in summaries:
        writer.writerow([
            s.date, s.sku_id, s.product_id, s.product_name,
            s.category_l1, s.category_l2, s.brand, s.avg_price,
            s.min_price, s.max_price, s.total_sales, s.shop_count, s.record_count
        ])
    return output.getvalue()


def save_category_to_oss(ossClient, config, summaries):
    filename = "category_daily_summary.csv"
    by_date = defaultdict(list)
    for s in summaries:
        by_date[s.date].append(s)
    for dt, day_summaries in sorted(by_date.items()):
        day_csv = to_category_summary_csv(day_summaries)
        ossClient.upload_string(
            ossClient.build_key("dws", f"dt={dt}", filename), day_csv
        )
    get_logger().info("Uploaded %d category summaries to DWS layer", len(summaries))


def to_category_summary_csv(summaries):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "category_l1", "category_l2", "avg_price", "min_price",
                     "max_price", "total_sales", "sku_count", "record_count"])
    for s in summaries:
        writer.writerow([
            s.date, s.category_l1, s.category_l2, s.avg_price,
            s.min_price, s.max_price, s.total_sales, s.sku_count, s.record_count
        ])
    return output.getvalue()


def save_overall_to_oss(ossClient, config, summaries):
    filename = "overall_daily_summary.csv"
    by_date = defaultdict(list)
    for s in summaries:
        by_date[s.date].append(s)
    for dt, day_summaries in sorted(by_date.items()):
        day_csv = to_overall_summary_csv(day_summaries)
        ossClient.upload_string(
            ossClient.build_key("dws", f"dt={dt}", filename), day_csv
        )
    get_logger().info("Uploaded %d overall summaries to DWS layer", len(summaries))


def to_overall_summary_csv(summaries):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "avg_price", "min_price", "max_price",
                     "total_sales", "total_skus", "total_records"])
    for s in summaries:
        writer.writerow([
            s.date, s.avg_price, s.min_price, s.max_price,
            s.total_sales, s.total_skus, s.total_records
        ])
    return output.getvalue()


# ========== ADS 层 OSS 上传 ==========

def save_ads_to_oss(ossClient, config, indices,
                    overall_summaries, reportGenerator):
    # overall_index.json
    ossClient.upload_string(
        ossClient.build_key("ads", "", "overall_index.json"),
        reportGenerator.to_json(indices.overall_indices)
    )

    # category_index.json
    ossClient.upload_string(
        ossClient.build_key("ads", "", "category_index.json"),
        reportGenerator.to_json(indices.category_indices)
    )

    # sku_index.json
    ossClient.upload_string(
        ossClient.build_key("ads", "", "sku_index.json"),
        reportGenerator.to_json(indices.sku_indices)
    )

    # top_movers.json
    ossClient.upload_string(
        ossClient.build_key("ads", "", "top_movers.json"),
        reportGenerator.to_json(indices.top_movers)
    )

    # daily_report.json
    ossClient.upload_string(
        ossClient.build_key("ads", "", "daily_report.json"),
        reportGenerator.generate_daily_report(indices.overall_indices, overall_summaries)
    )

    get_logger().info("Uploaded ADS layer to OSS")


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)


if __name__ == "__main__":
    main()
