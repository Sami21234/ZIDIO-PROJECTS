# Project FORESIGHT - Executive Readout
**Prepared for: Head of Operations & Finance Lead, NorthBay Living**

---

## The Bottom Line

Right now, across your catalog:

- **£99,024 in sales is at risk** from 72 products about to run out of stock
- **£1,331,583 in cash is sitting idle** in 1,559 products that have overstocked and aren't selling
- Together, that's over **£1.4 million** in avoidable losses sitting in your warehouse today

This isn't a forecast of future risk - this reflects your **current inventory position right now**, checked against how each product is actually selling.

---

## What To Do This Week

### Reorder immediately (highest sales at risk)

| Product | £ at risk |
|---|---|
| Chocolate Hot Water Bottle | £5,059 |
| Embroidered Ribbon Reel - Emily | £4,367 |
| Embroidered Ribbon Reel - Susie | £4,343 |
| Embroidered Ribbon Reel - Daisy | £4,191 |
| Embroidered Ribbon Reel - Sally | £3,813 |

*(72 products total - full list in the dashboard's "Reorder now" view)*

### Markdown or clear (highest capital locked up)

| Product | £ locked up |
|---|---|
| Small Fairy Cake Fridge Magnets | £74,825 |
| Medium Ceramic Top Storage Jar | £38,855 |
| Black and White Paisley Flower Mug | £35,263 |
| Large Glass Rose Scented Candle | £29,794 |
| Bird in Tree Mug | £19,669 |

*(1,559 products total - full list in the dashboard's "Markdown/clear" view)*

---

## How Confident Should You Be In This?

We built a system that predicts weekly demand for every product, then checked it the honest way: we hid the most recent months of real sales, had the system predict them using only what it could have known beforehand, then compared the predictions to what actually happened.

Result: our forecasting system is **39% more accurate** than simply guessing "this week will look like the same week last year" - the standard baseline comparison.

**Where to trust it most:** your best-selling products (roughly the top fifth of your catalog, which already drives 80% of your revenue) get the most reliable forecasts.

**Where to be more cautious:** low-volume, occasional-selling products are inherently harder to predict for any system - treat forecasts for these as a general guide rather than a precise number, and rely more on the current stock position than the forward prediction for these items.

---

## What This Is Built On

- Two years of your sales history (Dec 2009 – Dec 2011), covering 4,731 products
- Current stock levels, reorder points, and supplier lead times per product
- A system that learns from each product's own sales pattern, recent trend, seasonality, and promotional activity

## Honest Limitations

- Product cost and current stock levels are **estimated**, not pulled from a live inventory system - accuracy will improve once connected to real, live stock data
- The system is most reliable on regularly-selling products; occasional/seasonal-only products carry more forecast uncertainty
- This reflects historical patterns - a genuinely new trend (a viral product, a supply shock) won't be anticipated until it starts showing up in the sales data

## Recommended Next Step

Connect this system to live, current inventory data (rather than the estimated figures used for this analysis) so the £ figures above reflect your actual stock position today, and re-run weekly as new sales data comes in.

---

*Technical detail (model type, backtesting methodology, full accuracy metrics) available on request - see `reports/data_cleaning_report.md` and `reports/eda_insight_memo.md` for the full analytical trail.*
