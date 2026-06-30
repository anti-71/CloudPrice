"""Cloud Price Index — pandas 逐天流水线"""

import argparse, sys, io, csv, pandas as pd
from datetime import datetime, timedelta

from src.compute.data_aggregator import DataAggregator
from src.compute.data_cleaner import DataCleaner
from src.compute.index_computer import IndexComputer
from src.ingestion.mock_data_generator import MockDataGenerator
from src.report.report_generator import ReportGenerator
from src.storage.oss_client import OssClient
from src.util.config_loader import ConfigLoader
from src.util.logger_config import setup_logger


def main():
    log = setup_logger("main")
    log.info("=" * 50)
    log.info("  Cloud Price Index — pandas Pipeline")
    log.info("=" * 50)

    config = ConfigLoader()
    if not config.oss_enabled:
        log.error("OSS_ENABLED required"); sys.exit(1)

    args = _parse_args()
    start = args.get("start") or config.start_date
    end = args.get("end") or config.end_date
    if args.get("date"):
        start = end = args["date"]
    dates = _date_range(start, end)
    log.info("Dates: %s → %s (%d days)", start, end, len(dates))

    oss = OssClient(config)
    gen = MockDataGenerator(config)
    cleaner = DataCleaner()
    agg = DataAggregator()
    ic = IndexComputer(config.base_date)
    reporter = ReportGenerator()

    total_raw, total_clean = 0, 0
    sku_frames, cat_frames, ovr_frames = [], [], []

    for i, dt in enumerate(dates, 1):
        # ODS
        raw = gen.generate(dt, dt)
        total_raw += len(raw)
        _df_to_oss(oss, config, "ods", dt, "product_price_raw.csv", raw)

        # DWD
        clean = cleaner.clean(raw)
        total_clean += len(clean)
        _df_to_oss(oss, config, "dwd", dt, "product_price_clean.csv", clean)

        # DWS
        ag = agg.aggregate(clean)
        sku_frames.append(ag["sku"])
        cat_frames.append(ag["cat"])
        ovr_frames.append(ag["ovr"])

        if i % 30 == 0:
            log.info("  [%d/%d] %s  raw=%d clean=%d", i, len(dates), dt, total_raw, total_clean)

    # Concat all DWS
    sku_all = pd.concat(sku_frames, ignore_index=True)
    cat_all = pd.concat(cat_frames, ignore_index=True)
    ovr_all = pd.concat(ovr_frames, ignore_index=True)

    _df_to_oss(oss, config, "dws", "", "sku_daily_summary.csv", sku_all)
    _df_to_oss(oss, config, "dws", "", "category_daily_summary.csv", cat_all)
    _df_to_oss(oss, config, "dws", "", "overall_daily_summary.csv", ovr_all)

    # ADS
    log.info("Computing indices...")
    idx = ic.compute(sku_all, cat_all, ovr_all)
    oss.upload_string(oss.build_key("ads", "", "overall_index.json"), reporter.to_json_df(idx["overall"], "date", ["index", "change_pct"]))
    oss.upload_string(oss.build_key("ads", "", "category_index.json"), reporter.to_json_df(idx["category"], "category"))
    oss.upload_string(oss.build_key("ads", "", "sku_index.json"), reporter.to_json_df(idx["sku"], "sku_id"))
    oss.upload_string(oss.build_key("ads", "", "top_movers.json"), reporter.to_json_df(idx["top"], "sku_id"))
    oss.upload_string(oss.build_key("ads", "", "daily_report.json"),
                      reporter.generate_daily_report_df(idx["overall"], ovr_all))

    log.info("=" * 50)
    log.info("  Done! %d days, ODS=%d, DWD=%d", len(dates), total_raw, total_clean)
    log.info("  DWS: %d SKU / %d cat / %d ovr", len(sku_all), len(cat_all), len(ovr_all))
    log.info("  ADS: %d ovr / %d cat / %d SKU indices", len(idx["overall"]), len(idx["category"]), len(idx["sku"]))
    log.info("=" * 50)


# ── helpers ──

def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--date"); p.add_argument("--start-date"); p.add_argument("--end-date")
    a = p.parse_args()
    return {"date": a.date, "start": a.start_date, "end": a.end_date}

def _date_range(s, e):
    d = datetime.strptime(s, "%Y-%m-%d")
    end = datetime.strptime(e, "%Y-%m-%d")
    return [(d + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end - d).days + 1)]

def _df_to_oss(oss, config, layer, subdir, filename, df):
    if df is None or len(df) == 0:
        return
    out = io.StringIO()
    df.to_csv(out, index=False)
    key = oss.build_key(layer, f"dt={subdir}" if subdir else "", filename)
    oss.upload_string(key, out.getvalue())

if __name__ == "__main__":
    main()
