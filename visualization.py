"""价格指数折线图 — 从 ClickHouse SQL 查询 + matplotlib 绘图"""

import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from src.storage.clickhouse_client import ClickHouseClient
from src.util.config_loader import ConfigLoader

if os.getenv("CI"):
    print("CI runner: ClickHouse unreachable, skipping chart")
    sys.exit(0)

config = ConfigLoader()
ch = ClickHouseClient(config)

# ── 1. ClickHouse SQL 查询 ──
result = ch.query("""
    SELECT date, index_value
    FROM ads_price_index_daily
    WHERE index_type = 'overall'
    ORDER BY date
    FORMAT TabSeparated
""")

dates, values = [], []
for line in result.strip().split("\n"):
    if line.strip():
        d, v = line.split("\t")
        dates.append(datetime.strptime(d, "%Y-%m-%d"))
        values.append(float(v))

# ── 2. 画图 ──
fig, ax = plt.subplots(figsize=(18, 6))
ax.plot(dates, values, linewidth=1.0, color="#2563eb")
ax.axhline(y=100, color="gray", linestyle="--", linewidth=0.6, alpha=0.4)
ax.set_title("Cloud Price Index (2023-2026) - ClickHouse SQL", fontsize=13)
ax.set_ylabel("Price Index (base=100)")
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
plt.xticks(rotation=45)
plt.grid(alpha=0.2)
plt.tight_layout()
plt.savefig("price_index_trend.png", dpi=150)

print(f"Done: price_index_trend.png")
print(f"   {len(dates)} days, min={min(values):.2f}, max={max(values):.2f}")
