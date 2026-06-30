"""集成测试 — pandas 版本"""
import json
import pytest
from src.compute.data_aggregator import DataAggregator
from src.compute.data_cleaner import DataCleaner
from src.compute.index_computer import IndexComputer
from src.ingestion.mock_data_generator import MockDataGenerator
from src.report.report_generator import ReportGenerator
from src.util.config_loader import ConfigLoader


def test_end_to_end_pipeline():
    config = ConfigLoader()
    gen = MockDataGenerator(config, seed=42)
    cleaner = DataCleaner()
    agg = DataAggregator()
    ic = IndexComputer(config.base_date)
    reporter = ReportGenerator()

    raw = gen.generate("2023-06-01", "2023-06-03")
    assert len(raw) > 0, "ODS should not be empty"

    clean = cleaner.clean(raw)
    assert len(clean) <= len(raw), "Cleaned <= raw"

    ag = agg.aggregate(clean)
    assert len(ag["sku"]) > 0, "Should have SKU summaries"
    assert len(ag["cat"]) > 0, "Should have category summaries"
    assert len(ag["ovr"]) == 3, "Should have 3 overall summaries"

    idx = ic.compute(ag["sku"], ag["cat"], ag["ovr"])
    assert len(idx["overall"]) == 3
    assert len(idx["category"]) > 0

    report = reporter.generate_daily_report_df(idx["overall"], ag["ovr"])
    data = json.loads(report)
    assert len(data) == 3


def test_coverage():
    config = ConfigLoader()
    gen = MockDataGenerator(config, seed=1)
    cleaner = DataCleaner()
    raw = gen.generate("2023-06-01", "2023-06-05")
    clean = cleaner.clean(raw)
    coverage = clean["sku_id"].nunique() / raw["sku_id"].nunique()
    assert coverage >= 0.80, f"Coverage {coverage:.2%} < 80%"


def test_base_date_100():
    config = ConfigLoader()
    gen = MockDataGenerator(config, seed=42)
    cleaner = DataCleaner()
    agg = DataAggregator()
    ic = IndexComputer(config.base_date)
    raw = gen.generate(config.base_date, config.base_date)
    clean = cleaner.clean(raw)
    ag = agg.aggregate(clean)
    idx = ic.compute(ag["sku"], ag["cat"], ag["ovr"])
    for _, r in idx["overall"].iterrows():
        assert abs(r["index"] - 100.0) < 0.01


def test_json_format():
    config = ConfigLoader()
    gen = MockDataGenerator(config, seed=42)
    cleaner = DataCleaner()
    agg = DataAggregator()
    ic = IndexComputer(config.base_date)
    reporter = ReportGenerator()
    raw = gen.generate("2023-06-01", "2023-06-01")
    clean = cleaner.clean(raw)
    ag = agg.aggregate(clean)
    idx = ic.compute(ag["sku"], ag["cat"], ag["ovr"])

    overall = json.loads(reporter.to_json_df(idx["overall"], "date"))
    assert isinstance(overall, list)
    assert "date" in overall[0]
    assert "index" in overall[0]
