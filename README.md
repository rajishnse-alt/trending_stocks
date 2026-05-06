# Stocks in Trend

Daily NSE bhavcopy analysis — automatically generated from `stocks_in_trend_summary.txt`.

**Live page:** https://rajishnse-alt.github.io/trending_stocks/

The page shows the top 10 BUY (Pure_on_Volume HV-breakouts) and top 10 SELL
(HV-distribution) candidates from each trading day's bhavcopy, with:

- Verdict (STRONG BUY / BUY-LEAN / HOLD / SELL-LEAN / STRONG SELL)
- Pros & cons derived from price/volume signals
- screener.in fundamentals (MCap, P/E, ROCE, ROE, BookVal, dividend yield)
- screener.in qualitative pros & cons
- Direct link to each company's screener.in page

> **Disclaimer.** For educational and fundamental analysis only.
> Caution while investing. Nothing here is investment advice. Do your own
> research, consult a SEBI-registered advisor, and trade at your own risk.

## Methodology

BUY/SELL recommendations are based on the **Pure_on_Volume** screen — HVQ /
HVY / HVE volume breakouts gated by liquidity:

- **HVQ** = volume highest in the last 3 months
- **HVY** = volume highest in the last 1 year
- **HVE** = volume highest ever
- **CLV** = (close − low) / (high − low) × 2 − 1 — measures where the day closed inside its range

A breakout on a green day with CLV ≥ +0.7 is treated as accumulation (BUY bias).
A breakout on a red day with CLV ≤ −0.7 is treated as distribution (SELL bias).

The signals panel adds 52-week position, SMA stack, returns, volatility,
and delivery-percentage trend on top of the volume breakout to compute a
final verdict.

## Updating

The page is regenerated each trading day from `stocks_in_trend_summary.txt`
produced by the `bhavcopy_pipeline.py` job. Replace `index.html` with the
latest render and `git push` to refresh the live page.
