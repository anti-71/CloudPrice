"""CPI 真实数据流水线 — 2956 万行 → GB 级处理 → OSS"""

import glob, json, io
import pandas as pd
from src.storage.oss_client import OssClient
from src.util.config_loader import ConfigLoader


def main():
    config = ConfigLoader()
    oss = OssClient(config)

    print("Loading master data...")
    cats = pd.read_csv("data/categories.csv", encoding="gbk")
    prods = pd.read_csv("data/products.csv", encoding="gbk")

    leaf = cats[cats["hierarchy"] == 3]
    leaf_ids = set(leaf["category_id"])
    prods = prods[prods["category_id"].isin(leaf_ids)]
    prod_w = prods.set_index("product_id")["weight"].to_dict()
    prod_cat = prods.set_index("product_id")["category_id"].to_dict()
    cat_w = leaf.set_index("category_id")["weight"].to_dict()

    # 基期价格
    print("Loading base prices (2025-05-17)...")
    base_df = pd.read_csv("data/daily_price/daily_prices_20250517.csv", encoding="gbk")
    base_df = base_df[base_df["product_id"].isin(prods["product_id"])]
    base_prices = base_df.set_index("product_id")["price"].to_dict()

    files = sorted(glob.glob("data/daily_price/daily_prices_*.csv"))
    print(f"Processing {len(files)} files...")

    results = []
    for i, fp in enumerate(files):
        ds = fp[-12:-4]
        dt = f"{ds[:4]}-{ds[4:6]}-{ds[6:]}"

        df = pd.read_csv(fp, encoding="gbk")
        df = df[df["product_id"].isin(base_prices)].copy()
        df["base_price"] = df["product_id"].map(base_prices)
        df["index"] = df["price"] / df["base_price"] * 100
        df["weight"] = df["product_id"].map(prod_w).fillna(0.0001)
        df["category_id"] = df["product_id"].map(prod_cat).fillna("")

        # 类目加权
        num = df.groupby("category_id").apply(lambda x: (x["index"] * x["weight"]).sum(), include_groups=False)
        den = df.groupby("category_id")["weight"].sum()
        ci = pd.DataFrame({"cat_index": num / den}).reset_index()
        ci["cat_weight"] = ci["category_id"].map(cat_w).fillna(0.001)

        # 整体 = 类目加权
        ov = (ci["cat_index"] * ci["cat_weight"]).sum() / ci["cat_weight"].sum()

        results.append({"date": dt, "index": round(float(ov), 2)})
        if (i + 1) % 365 == 0:
            print(f"  {i+1}/{len(files)}  {dt}  idx={ov:.2f}")

    # 保存
    result_df = pd.DataFrame(results)
    print(f"Done: {len(result_df)} days, min={result_df['index'].min():.2f}, max={result_df['index'].max():.2f}")

    oss.upload_string(
        oss.build_key("real", "", "overall_index.json"),
        json.dumps(results, ensure_ascii=False, indent=2)
    )
    print("Uploaded to OSS.")


if __name__ == "__main__":
    main()
