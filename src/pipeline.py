"""
Project FORESIGHT — Data Pipeline
Transforms the raw Online Retail II extract (Invoice, StockCode, Description,
Quantity, InvoiceDate, Price, Customer ID, Country) into the 4-table schema
required by the engagement brief:

    sales_daily          (fact)  — one row per SKU per day
    sku_master            (dim)  — one row per SKU
    calendar               (dim)  — one row per date
    inventory_snapshots  (dim)  — periodic stock position per SKU

Run:
    python src/pipeline.py --input data/raw/online_retail_II.csv --outdir data/processed

Documented assumptions (see also reports/data_quality_memo.md):
  A1. A row is a "cancellation" if Invoice starts with 'C' — excluded from demand.
  A2. Rows with Quantity <= 0 or Price <= 0 are excluded (returns/adjustments/data errors).
  A2b. Administrative "stock codes" that are not real products are excluded: POSTAGE,
       bank charges, Amazon fees, manual adjustments, discounts, carriage, samples, etc.
       (see EXCLUDE_STOCK_CODES below). These are bookkeeping entries in the raw
       extract, not SKUs a client would stock or forecast.
  A3. unit_cost is NOT in the source data. We assume a category-level gross margin
      (55% for Seasonal/Decor, 50% general, 45% Stationery) and derive unit_cost
      from the SKU's typical list_price. This is an estimate, not observed cost.
  A4. inventory_snapshots does NOT exist in the source data at all. We simulate a
      weekly (s, S) inventory policy per SKU driven by that SKU's own observed
      demand (see build_inventory_snapshots). This is a documented simulation,
      not real client inventory data.
  A5. promo_flag in sales_daily is inferred: a day is "on promo" for a SKU if its
      average price that day is >= 15% below that SKU's rolling median price.
  A6. category / subcategory are assigned via keyword rules over Description,
      since the source data has no product hierarchy.
"""
import argparse         # allows to pass values through the command line.
import re       # regular expression used for keyword matching.
from pathlib import Path        # used to work with file/folder paths.
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)


# A6: lightweight keyword-based categorizer (documented assumption)
CATEGORY_RULES = [
    ("Seasonal & Christmas", r"christmas|xmas|advent|santa|snowman|holly|reindeer"),
    ("Kitchenware",           r"mug|cup|teapot|kitchen|bowl|plate|spoon|fork|tin\b|jar|cake|baking"),
    ("Home & Decor",          r"candle|light|lantern|frame|clock|cushion|holder|decoration|vase|hook"),
    ("Bags & Accessories",    r"bag|purse|wallet|umbrella|apron"),
    ("Stationery & Cards",    r"card|notebook|pen|pencil|paper|sticker|envelope|gift wrap|ribbon"),
    ("Toys & Games",          r"toy|game|puzzle|doll|robot|balloon"),
    ("Garden",                r"garden|plant pot|watering|outdoor"),
]
EXCLUDE_STOCK_CODES = {
    "POST", "DOT", "D", "M", "m", "C2", "BANK CHARGES", "AMAZONFEE",
    "CRUK", "ADJUST", "ADJUST2", "B", "S", "GIFT", "TEST001", "TEST002",
}

CATEGORY_MARGIN = {
    "Seasonal & Christmas": 0.55,
    "Kitchenware": 0.50,
    "Home & Decor": 0.50,
    "Bags & Accessories": 0.50,
    "Stationery & Cards": 0.45,
    "Toys & Games": 0.50,
    "Garden": 0.50,
    "General Merchandise": 0.50,  # fallback
}

# function to assigns the category for appeared keywords in the description.
def categorize(description: str) -> str:
    if not isinstance(description, str):
        return "General Merchandise"
    text = description.lower()      # converts description to lowercase.
    for category, pattern in CATEGORY_RULES:        # loop through  category rules.
        if re.search(pattern, text):
            return category
    return "General Merchandise"


# Step 1 — Load & clean raw extract

def load_and_clean(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="ISO-8859-1", dtype={"Invoice": str, "StockCode": str})
    df.columns = [c.strip() for c in df.columns]        # clean column names (by removing the leading/trailing spaces).

    before = len(df)        # counting the rows before cleaning.(useful for data-quality reporting.)

    # A1: drop cancellations (Invoice starting with C)
    df = df[~df["Invoice"].astype(str).str.startswith("C")]

    # A2: drop non-positive quantity/price and missing keys
    df = df.dropna(subset=["StockCode", "Description", "InvoiceDate"])
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]

    # basic type fixes
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["StockCode"] = df["StockCode"].str.strip().str.upper()
    df["Description"] = df["Description"].str.strip()

    # A2b: drop administrative / non-product stock codes
    n_before_admin = len(df)
    df = df[~df["StockCode"].isin(EXCLUDE_STOCK_CODES)]
    n_admin_removed = n_before_admin - len(df)
    if n_admin_removed:
        print(f"[clean] removed {n_admin_removed:,} rows with non-product "
              f"stock codes (postage/fees/adjustments/discounts)")

    # drop exact duplicate rows
    df = df.drop_duplicates()

    after = len(df)
    print(f"[clean] {before:,} raw rows -> {after:,} rows after cleaning "
          f"({before - after:,} removed: cancellations / invalid qty-price / dupes)")
    return df       # return the clean data.

# Step 2 — sku_master (dim)
def build_sku_master(df: pd.DataFrame) -> pd.DataFrame:
    # most frequent description per SKU (descriptions are sometimes inconsistent)
    desc = (df.groupby("StockCode")["Description"]
              .agg(lambda x: x.value_counts().idxmax())     # returns the most common or highest count of products.
              .rename("description"))
    
    launch_date = df.groupby("StockCode")["InvoiceDate"].min().rename("launch_date")        # launch_date of the product.
    list_price = df.groupby("StockCode")["Price"].median().rename("list_price")

    # combine the product information
    sku = pd.concat([desc, launch_date, list_price], axis=1).reset_index()
    sku = sku.rename(columns={"StockCode": "sku_id"})

    sku["category"] = sku["description"].apply(categorize)
    sku["subcategory"] = sku["description"].str.split().str[0].str.title()  # crude but documented
    sku["margin_assumed"] = sku["category"].map(CATEGORY_MARGIN)
    # A3: unit_cost derived from list_price and assumed category margin
    sku["unit_cost"] = (sku["list_price"] * (1 - sku["margin_assumed"])).round(2)
    sku["list_price"] = sku["list_price"].round(2)

    return sku[["sku_id", "description", "category", "subcategory",
                "launch_date", "unit_cost", "list_price"]]


# Step 3 — calendar (dim)
UK_FIXED_HOLIDAYS = {
    (1, 1): "New Year's Day",
    (12, 25): "Christmas Day",
    (12, 26): "Boxing Day",
}
PROMO_WINDOWS = [
    # (start_month, start_day, end_month, end_day, label)
    (11, 20, 11, 30, "Black Friday / Pre-Christmas"),
    (12, 1, 12, 24, "Christmas Sale"),
    (12, 26, 12, 31, "Boxing Day Sale"),
    (1, 1, 1, 15, "New Year Sale"),
    (6, 15, 7, 15, "Summer Sale"),
]

# function to build the calendar(dates)
def build_calendar(min_date, max_date) -> pd.DataFrame:
    dates = pd.date_range(min_date.normalize(), max_date.normalize(), freq="D")         # freq="D" means: daily.
    cal = pd.DataFrame({"date": dates})
    cal["week"] = cal["date"].dt.isocalendar().week.astype(int)
    cal["month"] = cal["date"].dt.month
    cal["month_name"] = cal["date"].dt.month_name()

# season function:
    def season(m):
        if m in (12, 1, 2):
            return "Winter"
        if m in (3, 4, 5):
            return "Spring"
        if m in (6, 7, 8):
            return "Summer"
        return "Autumn"
    cal["season"] = cal["month"].apply(season)

    # Holiday flag:
    cal["is_holiday"] = cal["date"].apply(
        lambda d: (d.month, d.day) in UK_FIXED_HOLIDAYS
    ).astype(int)

    def promo_event(d):
        for sm, sd, em, ed, label in PROMO_WINDOWS:
            start = pd.Timestamp(year=d.year, month=sm, day=sd)
            end = pd.Timestamp(year=d.year, month=em, day=ed)
            if start <= d <= end or (sm > em and (d >= start or d <= end)):
                return label
        return None
    cal["promo_event"] = cal["date"].apply(promo_event)

    return cal


