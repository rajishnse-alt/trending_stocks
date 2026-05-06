# Stocks in Trend

Daily NSE bhavcopy analysis — automatically generated from `stocks_in_trend_summary.txt`.

**Live page (Streamlit Cloud):** https://stocks-in-trend.streamlit.app/

The dashboard shows the top 10 BUY (Pure_on_Volume HV-breakouts) and top 10 SELL
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

## Files in this repo

| File                          | Purpose                                                |
|-------------------------------|--------------------------------------------------------|
| `streamlit_app.py`            | Streamlit dashboard — main entry point for the cloud   |
| `requirements.txt`            | `streamlit` (the only dep)                             |
| `stocks_in_trend_summary.txt` | Today's report — the data source the app reads         |
| `index.html`                  | Static fallback page (works on GitHub Pages too)       |
| `README.md`                   | This file                                              |

## Deploy to Streamlit Cloud (one-time)

1. Push this folder to the GitHub repo (use the `publish_to_github.sh` script).
2. Go to <https://share.streamlit.io> → sign in with GitHub.
3. Click **New app** → **Deploy a public app from GitHub**.
4. Repository: `rajishnse-alt/trending_stocks` · Branch: `main` · Main file: `streamlit_app.py`.
5. Click **Deploy**. First boot takes ~60 seconds. The URL is
   `https://<app-name>-<hash>.streamlit.app/` — pin a friendly subdomain in
   the app's *Settings → General → Custom subdomain* if you like.

## Updating each day

The page is regenerated automatically each trading day from
`stocks_in_trend_summary.txt` produced by the `bhavcopy_pipeline.py` job.
Re-run `publish_to_github.sh` after the pipeline finishes — Streamlit Cloud
notices the new commit and redeploys within ~30 seconds.
