"""
Stocks in Trend — Streamlit dashboard.
Reads `stocks_in_trend_summary.txt` (sitting next to this file) and renders the
top BUY / SELL candidates as interactive cards.
Deploy: push this repo to GitHub, then https://share.streamlit.io → "New app"
→ point at repo + branch + main file = `streamlit_app.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────── Page setup ────────────────────────
st.set_page_config(
    page_title="Stocks in Trend",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(
    """
    <style>
      /* Tighten up Streamlit's default vertical rhythm */
      .block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1280px; }
      h1 { letter-spacing: -0.02em; }
      [data-testid="stMetricValue"] { font-feature-settings: "tnum"; font-weight: 700; }
      .stock-symbol  { font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; font-weight: 700; font-size: 18px; letter-spacing: -0.01em; }
      .stock-name    { color: #94a3b8; font-size: 13px; margin-top: 2px; }
      .verdict-badge { display:inline-block; padding:3px 10px; border-radius:999px;
                       font-family:'JetBrains Mono', monospace; font-size:11px; font-weight:700;
                       letter-spacing:0.04em; border:1px solid currentColor; }
      .v-strong-buy  { color:#15803d; background:rgba(34,197,94,0.10); }
      .v-buy-lean    { color:#15803d; background:rgba(34,197,94,0.06); }
      .v-strong-sell { color:#b91c1c; background:rgba(239,68,68,0.10); }
      .v-sell-lean   { color:#b91c1c; background:rgba(239,68,68,0.06); }
      .v-hold        { color:#a16207; background:rgba(234,179,8,0.10); }
      .v-default     { color:#475569; background:rgba(148,163,184,0.10); }
      .meta-pill     { display:inline-block; padding:3px 10px; border-radius:999px;
                       font-family:'JetBrains Mono', monospace; font-size:11px;
                       background:rgba(148,163,184,0.12); color:#475569; margin-left:6px; }
      .net-pos { color:#15803d; font-weight:700; }
      .net-neg { color:#b91c1c; font-weight:700; }
      .net-zero{ color:#475569; font-weight:700; }
      .fund-row {
        font-family: 'JetBrains Mono', monospace; font-size: 12px; color:#475569;
        background: rgba(148,163,184,0.08); padding: 8px 12px; border-radius: 8px;
        margin-top: 6px;
      }
      .fund-row b { color:#0f172a; }
      .trade-plan {
        font-family: 'JetBrains Mono', monospace; font-size: 12px; color:#1e3a8a;
        background: rgba(59,130,246,0.10); padding: 8px 12px; border-radius: 8px;
        margin-top: 6px; line-height: 1.55;
      }
      .trade-plan b      { color:#0f172a; }
      .trade-plan .tp-entry  { color:#15803d; font-weight:700; }
      .trade-plan .tp-sl     { color:#b91c1c; font-weight:700; }
      .trade-plan .tp-target { color:#1d4ed8; font-weight:700; }
      .group-head-pro { color:#15803d; font-size: 11px; font-weight:700; letter-spacing:.08em;
                        text-transform:uppercase; margin-top:10px; }
      .group-head-con { color:#b91c1c; font-size: 11px; font-weight:700; letter-spacing:.08em;
                        text-transform:uppercase; margin-top:10px; }
      .pro-li { background: rgba(34,197,94,0.10); padding: 4px 10px; border-radius:6px;
                margin: 4px 0; font-size: 13px; }
      .con-li { background: rgba(239,68,68,0.10); padding: 4px 10px; border-radius:6px;
                margin: 4px 0; font-size: 13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────── Parser ────────────────────────────
SUMMARY_PATH = Path(__file__).parent / "stocks_in_trend_summary.txt"

VERDICT_CLASS = {
    "STRONG BUY":  "v-strong-buy",
    "BUY-LEAN":    "v-buy-lean",
    "BUY":         "v-buy-lean",
    "STRONG SELL": "v-strong-sell",
    "SELL-LEAN":   "v-sell-lean",
    "SELL":        "v-sell-lean",
    "HOLD / MIXED":"v-hold",
}


def parse_block(block: str) -> dict | None:
    head = re.match(
        r"\s*•\s+(\S+)\s+\((.+?)\)\s+close\s+₹([\d.]+)\s+([+-]?[\d.]+)%\s+bias\s+(\S+)",
        block,
    )
    if not head:
        return None

    verdict_match = re.search(
        r"→\s+(.+?)\s+\(tech=(\S+),\s+signal net\s+([+-]?\d+)\)", block
    )

    def grab_section(label: str) -> list[str]:
        m = re.search(
            rf"{re.escape(label)}\s*\n((?:\s+-\s.+\n?)+)", block
        )
        if not m:
            return []
        return [
            re.sub(r"^\s*-\s+", "", line).strip()
            for line in m.group(1).strip().splitlines()
            if line.strip().startswith("-")
        ]

    def grab_trade_plan() -> dict:
        """Pull the four BUY trade-management levels from the
        'TRADE PLAN (BUY):' block if present. Returns empty strings
        for any level that isn't in the block (SELL picks won't have
        a trade plan at all).
        """
        out = {"entry": "", "strict_sl": "", "best_sl": "", "target_1": ""}
        patterns = {
            # The price token allows ₹ + digits + optional commas/decimals
            "entry":     r"Entry zone\s*\(probable\):\s+above\s+(₹[\d.,]+)",
            "strict_sl": r"Strict stop-loss:\s+(₹[\d.,]+)",
            "best_sl":   r"Best stop-loss:\s+(₹[\d.,]+)",
            "target_1":  r"Target-1:\s+(₹[\d.,]+)",
        }
        for key, pat in patterns.items():
            m = re.search(pat, block)
            if m:
                out[key] = m.group(1)
        return out

    fund_match = re.search(r"FUNDAMENTALS \(screener\.in\):\s+(.+)", block)
    url_match = re.search(r"(https?://www\.screener\.in/\S+)", block)

    return {
        "symbol":          head.group(1),
        "name":            head.group(2).strip(),
        "price":           float(head.group(3)),
        "change_pct":      float(head.group(4)),
        "bias":            head.group(5),
        "verdict":         (verdict_match.group(1).strip() if verdict_match else ""),
        "tech":            (verdict_match.group(2) if verdict_match else ""),
        "net":             int(verdict_match.group(3)) if verdict_match else 0,
        "trade_plan":      grab_trade_plan(),
        "signal_pros":     grab_section("PROS (signals):"),
        "signal_cons":     grab_section("CONS (signals):"),
        "screener_pros":   grab_section("PROS (screener.in):"),
        "screener_cons":   grab_section("CONS (screener.in):"),
        "fundamentals":    fund_match.group(1).strip() if fund_match else "",
        "url":             url_match.group(1) if url_match else "",
    }


def split_blocks(section_text: str) -> list[str]:
    blocks, current = [], []
    for line in section_text.splitlines():
        if re.match(r"\s*•\s+\S", line):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current is not None:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return [b for b in blocks if b.strip()]


@st.cache_data(show_spinner=False, ttl=900)
def parse_summary(text: str) -> dict:
    generated = re.search(r"generated\s+(.+)$", text, flags=re.M)
    pov_hits  = re.search(r"Pure_on_Volume hits \(BUY\):\s+(\d+)", text)
    rec       = re.search(r"Recommendations:\s+(\d+)\s+BUY\s+\+\s+(\d+)\s+SELL", text)

    # Flexible Top-N matching — the pipeline currently writes "Top 20
    # BUY candidates:" / "Top 20 SELL candidates ..." but historically
    # used "Top 10". Match any positive integer so the dashboard keeps
    # working regardless of how many picks the pipeline emits.
    buy_sec  = re.search(
        r"Top\s+\d+\s+BUY candidates:.*?\n-+\n(.*?)"
        r"(?=Top\s+\d+\s+SELL candidates|\Z)",
        text, flags=re.S,
    )
    sell_sec = re.search(
        r"Top\s+\d+\s+SELL candidates.*?\n-+\n(.*?)(?=\n—|\Z)",
        text, flags=re.S,
    )

    buys  = [parse_block(b) for b in split_blocks(buy_sec.group(1))]  if buy_sec  else []
    sells = [parse_block(b) for b in split_blocks(sell_sec.group(1))] if sell_sec else []

    return {
        "generated":  generated.group(1).strip() if generated else "",
        "pov_hits":   int(pov_hits.group(1)) if pov_hits else 0,
        "buy_count":  int(rec.group(1)) if rec else 0,
        "sell_count": int(rec.group(2)) if rec else 0,
        "buys":       [b for b in buys  if b],
        "sells":      [s for s in sells if s],
    }


# ─────────────────────────────────────────── Load ──────────────────────────────
if not SUMMARY_PATH.exists():
    st.error(
        "`stocks_in_trend_summary.txt` not found next to this script. "
        "Add the file to the repo and redeploy."
    )
    st.stop()

text = SUMMARY_PATH.read_text(encoding="utf-8")
data = parse_summary(text)

# ─────────────────────────────────────────── Header ────────────────────────────
st.markdown("# 📈 Stocks in Trend")
st.caption(
    f"NSE bhavcopy analysis · {data['generated'] or 'date not detected'} · "
    "Pure-on-Volume + screener.in fundamentals"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("BUY recommendations", data["buy_count"])
c2.metric("SELL recommendations", data["sell_count"])
c3.metric("Pure-on-Volume hits", data["pov_hits"])
c4.metric("Showing", f"{len(data['buys']) + len(data['sells'])} stocks")

st.warning(
    "**Disclaimer.** For educational and fundamental analysis only. "
    "Nothing here is investment advice. Do your own research, consult a "
    "SEBI-registered advisor, and trade at your own risk.",
    icon="⚠️",
)


# ─────────────────────────────────────────── Card renderer ─────────────────────
def render_signals(items: list[str], kind: str) -> None:
    if not items:
        return
    cls = "pro-li" if kind == "pro" else "con-li"
    head_cls = "group-head-pro" if kind == "pro" else "group-head-con"
    label = "Pros" if kind == "pro" else "Cons"
    st.markdown(f'<div class="{head_cls}">{label}</div>', unsafe_allow_html=True)
    html = "".join(f'<div class="{cls}">{it}</div>' for it in items)
    st.markdown(html, unsafe_allow_html=True)


def render_trade_plan(tp: dict) -> None:
    """Render the BUY trade-management block (entry / stops / target)."""
    if not tp or not any(tp.values()):
        return
    entry = tp.get("entry") or "—"
    strict_sl = tp.get("strict_sl") or "—"
    best_sl = tp.get("best_sl") or "—"
    target_1 = tp.get("target_1") or "—"
    st.markdown(
        '<div class="trade-plan">'
        f'<b>Entry</b> above <span class="tp-entry">{entry}</span>'
        f' · <b>Strict SL</b> <span class="tp-sl">{strict_sl}</span>'
        f' · <b>Best SL</b> <span class="tp-sl">{best_sl}</span>'
        f' · <b>Target-1</b> <span class="tp-target">{target_1}</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_card(stock: dict, kind: str) -> None:
    pct = stock["change_pct"]
    pct_str = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
    pct_color = "normal"
    if pct > 0: pct_color = "normal"
    if pct < 0: pct_color = "inverse"

    verdict = stock["verdict"] or stock["bias"].replace("_", " ")
    verdict_class = VERDICT_CLASS.get(verdict.upper().strip(), "v-default")

    net = stock["net"]
    net_class = "net-pos" if net > 0 else ("net-neg" if net < 0 else "net-zero")
    net_str = f"+{net}" if net > 0 else f"{net}"

    with st.container(border=True):
        h1, h2 = st.columns([3, 1.2])
        with h1:
            st.markdown(
                f'<div class="stock-symbol">{stock["symbol"]}</div>'
                f'<div class="stock-name">{stock["name"]}</div>',
                unsafe_allow_html=True,
            )
        with h2:
            st.metric("Close", f"₹{stock['price']:,.2f}", pct_str, delta_color=pct_color)

        st.markdown(
            f'<span class="verdict-badge {verdict_class}">{verdict}</span>'
            f'<span class="meta-pill">bias {stock["bias"]}</span>'
            f'<span class="meta-pill">net <span class="{net_class}">{net_str}</span></span>',
            unsafe_allow_html=True,
        )

        # BUY-only: trade-management plan
        if kind == "buy":
            render_trade_plan(stock.get("trade_plan") or {})

        render_signals(stock["signal_pros"], "pro")
        render_signals(stock["signal_cons"], "con")

        if stock["fundamentals"]:
            st.markdown(
                f'<div class="fund-row">{stock["fundamentals"]}</div>',
                unsafe_allow_html=True,
            )

        if stock["screener_pros"] or stock["screener_cons"]:
            with st.expander("screener.in pros & cons"):
                render_signals(stock["screener_pros"], "pro")
                render_signals(stock["screener_cons"], "con")

        if stock["url"]:
            st.markdown(f"[screener.in/{stock['symbol']} ↗]({stock['url']})")


# ─────────────────────────────────────────── Tabs ──────────────────────────────
buy_tab, sell_tab, raw_tab = st.tabs(
    [
        f"💚  BUY  ({len(data['buys'])})",
        f"❤️  SELL  ({len(data['sells'])})",
        "📄  Raw text",
    ]
)

with buy_tab:
    if not data["buys"]:
        st.info("No BUY candidates parsed from the summary.")
    else:
        cols = st.columns(2)
        for i, stock in enumerate(data["buys"]):
            with cols[i % 2]:
                render_card(stock, "buy")

with sell_tab:
    if not data["sells"]:
        st.info("No SELL candidates parsed from the summary.")
    else:
        cols = st.columns(2)
        for i, stock in enumerate(data["sells"]):
            with cols[i % 2]:
                render_card(stock, "sell")

with raw_tab:
    st.code(text, language="text")
    st.download_button(
        "Download stocks_in_trend_summary.txt",
        data=text,
        file_name="stocks_in_trend_summary.txt",
        mime="text/plain",
    )

# ─────────────────────────────────────────── Footer ────────────────────────────
st.divider()
st.caption(
    "**Methodology.** BUY/SELL recommendations are based on the *Pure_on_Volume* "
    "screen — HVQ / HVY / HVE volume breakouts gated by liquidity. Pros & cons "
    "(signals) are derived from price/volume panel data: 52-week position, SMA "
    "stack, returns, volatility, delivery & volume trend, CLV. Pros & cons "
    "(screener.in) are scraped from the company's screener.in page. "
    "BUY trade plan: Entry = fib-0.55 of today's range; Strict SL = fib-0.44 "
    "of prev day's range; Best SL = previous 1-week swing low; "
    "Target-1 = prev_high + (prev_high - prev_low)."
)
