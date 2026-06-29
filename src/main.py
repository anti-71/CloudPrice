#!/usr/bin/env python3
"""
Cloud Price Index 主入口 — 逐天流水线，支持 GB 级/三年数据

数据分层：ODS → DWD → DWS → ADS
每层数据逐天生成、逐天上传 OSS，不积压内存
"""

import argparse
import csv
import io
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

from src.compute.data_aggregator import DataAggregator
from src.compute.data_cleaner import DataCleaner
from src.compute.index_computer import IndexComputer
from src.ingestion.mock_data_generator import MockDataGenerator
from src.report.report_generator import ReportGenerator
from src.storage.oss_client import OssClient
from src.util.config_loader import ConfigLoader
from src.util.logger_config import setup_logger


def main():
    logger = setup_logger("main")
    logger.info("=" * 55)
    logger.info("  Cloud Price Index — Day-by-Day Pipeline")
    logger.info("=" * 55)

    config = ConfigLoader()
    logger.info("Config: sku=%d, dirty=%.0f%%", config.sku_count, config.dirty_data_rate * 100)

    if not config.oss_enabled:
        logger.error("OSS_ENABLED required"); sys.exit(1)

    # ── 日期 ──
    args = _parse_args()
    start, end = args.get("start") or config.start_date, args.get("end") or config.end_date
    if args.get("date"):
        start = end = args["date"]
    dates = _date_range(start, end)
    logger.info("Dates: %s → %s (%d days)", start, end, len(dates))

    # ── 组件 ──
    oss = OssClient(config)
    gen = MockDataGenerator(config)
    cleaner = DataCleaner()
    agg = DataAggregator()
    idx_computer = IndexComputer(config.base_date)
    reporter = ReportGenerator()

    # ── 累加器 ──
    total_raw = total_clean = 0
    sku_acc, cat_acc, ovr_acc = [], [], []

    # ── 逐天 ──
    for i, dt in enumerate(dates, 1):
        # 1. ODS
        raw = gen.generate(dt, dt)
        total_raw += len(raw)
        _csv_to_oss(oss, config, "ods", dt, "product_price_raw.csv", raw,
                    ["date","sku_id","product_id","product_name","category_l1",
                     "category_l2","brand","platform","shop_id","price",
                     "sales","is_promo","collect_time"],
                    lambda r: [r.date,r.sku_id,r.product_id,r.product_name,
                               r.category_l1,r.category_l2,r.brand,r.platform,
                               r.shop_id,r.price,r.sales,r.is_promo,r.collect_time])

        # 2. DWD
        clean = cleaner.clean(raw)
        total_clean += len(clean)
        _csv_to_oss(oss, config, "dwd", dt, "product_price_clean.csv", clean,
                    ["date","sku_id","product_id","product_name","category_l1",
                     "category_l2","brand","platform","shop_id","price",
                     "sales","is_promo","collect_time"],
                    lambda r: [r.date,r.sku_id,r.product_id,r.product_name,
                               r.category_l1,r.category_l2,r.brand,r.platform,
                               r.shop_id,r.price,r.sales,r.is_promo,r.collect_time])

        # 3. DWS — 汇总 & 累加
        day_agg = agg.aggregate(clean)
        sku_acc.extend(day_agg.sku_summaries)
        cat_acc.extend(day_agg.category_summaries)
        ovr_acc.extend(day_agg.overall_summaries)

        if i % 30 == 0:
            logger.info("  [%d/%d] %s  raw=%d clean=%d", i, len(dates), dt, total_raw, total_clean)

    # ── 上传 DWS ──
    _csv_to_oss(oss, config, "dws", "", "sku_daily_summary.csv", sku_acc,
                ["date","sku_id","product_id","product_name","category_l1",
                 "category_l2","brand","avg_price","min_price","max_price",
                 "total_sales","shop_count","record_count"],
                lambda s: [s.date,s.sku_id,s.product_id,s.product_name,
                           s.category_l1,s.category_l2,s.brand,s.avg_price,
                           s.min_price,s.max_price,s.total_sales,s.shop_count,s.record_count])
    _csv_to_oss(oss, config, "dws", "", "category_daily_summary.csv", cat_acc,
                ["date","category_l1","category_l2","avg_price","min_price",
                 "max_price","total_sales","sku_count","record_count"],
                lambda s: [s.date,s.category_l1,s.category_l2,s.avg_price,
                           s.min_price,s.max_price,s.total_sales,s.sku_count,s.record_count])
    _csv_to_oss(oss, config, "dws", "", "overall_daily_summary.csv", ovr_acc,
                ["date","avg_price","min_price","max_price","total_sales","total_skus","total_records"],
                lambda s: [s.date,s.avg_price,s.min_price,s.max_price,s.total_sales,s.total_skus,s.total_records])

    # ── 4. ADS ──
    logger.info("Computing indices...")
    indices = idx_computer.compute(sku_acc, cat_acc, ovr_acc)

    oss.upload_string(oss.build_key("ads","","overall_index.json"), reporter.to_json(indices.overall_indices))
    oss.upload_string(oss.build_key("ads","","category_index.json"), reporter.to_json(indices.category_indices))
    oss.upload_string(oss.build_key("ads","","sku_index.json"), reporter.to_json(indices.sku_indices))
    oss.upload_string(oss.build_key("ads","","top_movers.json"), reporter.to_json(indices.top_movers))
    oss.upload_string(oss.build_key("ads","","daily_report.json"),
                      reporter.generate_daily_report(indices.overall_indices, ovr_acc))

    # ── 报告 ──
    logger.info("=" * 55)
    logger.info("  Done! %d days, ODS=%d, DWD=%d", len(dates), total_raw, total_clean)
    logger.info("  DWS: %d SKU, %d cat, %d ovr", len(sku_acc), len(cat_acc), len(ovr_acc))
    logger.info("  ADS: %d ovr / %d cat / %d SKU indices",
                len(indices.overall_indices), len(indices.category_indices), len(indices.sku_indices))
    logger.info("=" * 55)


# ───────────────────── helpers ─────────────────────

def _parse_args() -> dict:
    p = argparse.ArgumentParser(description="Cloud Price Index")
    p.add_argument("--date"); p.add_argument("--start-date"); p.add_argument("--end-date")
    a = p.parse_args()
    return {"date": a.date, "start": a.start_date, "end": a.end_date}


def _date_range(start: str, end: str) -> List[str]:
    d = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    return [(d + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((e - d).days + 1)]


def _csv_to_oss(oss, config, layer, subdir, filename, items, headers, row_fn):
    if not items:
        return
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(headers)
    for it in items:
        w.writerow(row_fn(it))
    key = oss.build_key(layer, f"dt={subdir}" if subdir else "", filename)
    oss.upload_string(key, out.getvalue())


if __name__ == "__main__":
    main()
