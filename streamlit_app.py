"""
Stocks in Trend — Streamlit dashboard.
Reads `stocks_in_trend_summary.txt` (sitting next to this file) and renders the
top BUY / SELL candidates as interactive cards.
Deploy: push this repo to GitHub, then https://share.streamlit.io → "New app"
→ point at repo + branch + main file = `streamlit_app.py`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────── Page setup ────────────────────────
st.set_page_config(
    page_title="Stocks in Trend",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────── Theme toggle ─────────────────────
# Two palettes — light (default) and dark. Tracked in st.session_state so the
# choice survives reruns within a session. The toggle button itself sits to
# the right of the page title (rendered a few lines below).
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"
DARK = st.session_state["theme"] == "dark"

if DARK:
    P = {
        "bg":         "#0b1220",
        "fg":         "#e2e8f0",
        "muted":      "#94a3b8",
        "border":     "rgba(148,163,184,0.20)",
        "green_bg":   "rgba(34,197,94,0.18)",
        "green_fg":   "#4ade80",
        "red_bg":     "rgba(239,68,68,0.18)",
        "red_fg":     "#f87171",
        "blue_bg":    "rgba(59,130,246,0.20)",
        "blue_fg":    "#60a5fa",
        "amber_bg":   "rgba(234,179,8,0.18)",
        "amber_fg":   "#fbbf24",
        "neutral_bg": "rgba(148,163,184,0.20)",
        "neutral_fg": "#cbd5e1",
        "fund_bg":    "rgba(148,163,184,0.10)",
        "tp_bg":      "rgba(59,130,246,0.15)",
        "tp_fg":      "#93c5fd",
        "tp_dim":     "#94a3b8",
        "strong_b":   "#e2e8f0",
    }
else:
    P = {
        "bg":         "#ffffff",
        "fg":         "#0f172a",
        "muted":      "#475569",
        "border":     "rgba(148,163,184,0.35)",
        "green_bg":   "rgba(34,197,94,0.10)",
        "green_fg":   "#15803d",
        "red_bg":     "rgba(239,68,68,0.10)",
        "red_fg":     "#b91c1c",
        "blue_bg":    "rgba(59,130,246,0.10)",
        "blue_fg":    "#1d4ed8",
        "amber_bg":   "rgba(234,179,8,0.10)",
        "amber_fg":   "#a16207",
        "neutral_bg": "rgba(148,163,184,0.10)",
        "neutral_fg": "#475569",
        "fund_bg":    "rgba(148,163,184,0.08)",
        "tp_bg":      "rgba(59,130,246,0.10)",
        "tp_fg":      "#1e3a8a",
        "tp_dim":     "#475569",
        "strong_b":   "#0f172a",
    }

st.markdown(
    f"""
    <style>
      /* Streamlit chrome ---------------------------------------------------- */
      .stApp {{ background: {P['bg']}; color: {P['fg']}; }}
      .block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1280px; }}
      h1, h2, h3, h4 {{ color: {P['fg']}; letter-spacing: -0.02em; }}
      p, label, span, div, li {{ color: {P['fg']}; }}
      [data-testid="stCaptionContainer"], .stCaption,
      [data-testid="stMarkdownContainer"] small {{ color: {P['muted']} !important; }}
      [data-testid="stMetricLabel"] {{ color: {P['muted']}; }}
      [data-testid="stMetricValue"] {{ color: {P['fg']}; font-feature-settings: "tnum"; font-weight: 700; }}
      /* Tabs */
      [data-baseweb="tab-list"] {{ border-bottom-color: {P['border']}; }}
      [data-baseweb="tab"] {{ color: {P['muted']}; }}
      [data-baseweb="tab"][aria-selected="true"] {{ color: {P['fg']}; }}
      /* Bordered containers (used for cards) */
      [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: {P['border']} !important; }}
      /* Code block (Raw text tab) */
      pre, code {{ color: {P['fg']}; }}
      [data-testid="stCodeBlock"] {{ background: {P['fund_bg']} !important; }}
      /* Dataframe (Bulk Deals tab) */
      [data-testid="stDataFrame"] {{ color: {P['fg']}; }}
      /* Theme toggle button styling */
      .theme-toggle button {{
          background: {P['neutral_bg']} !important;
          color: {P['fg']} !important;
          border: 1px solid {P['border']} !important;
          border-radius: 999px !important;
          font-weight: 600 !important;
      }}

      /* Custom card components -------------------------------------------- */
      .stock-symbol  {{ font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; font-weight: 700; font-size: 18px; letter-spacing: -0.01em; color: {P['fg']}; }}
      .stock-name    {{ color: {P['muted']}; font-size: 13px; margin-top: 2px; }}
      .verdict-badge {{ display:inline-block; padding:3px 10px; border-radius:999px;
                        font-family:'JetBrains Mono', monospace; font-size:11px; font-weight:700;
                        letter-spacing:0.04em; border:1px solid currentColor; }}
      .v-strong-buy  {{ color:{P['green_fg']}; background:{P['green_bg']}; }}
      .v-buy-lean    {{ color:{P['green_fg']}; background:{P['green_bg']}; }}
      .v-strong-sell {{ color:{P['red_fg']};   background:{P['red_bg']}; }}
      .v-sell-lean   {{ color:{P['red_fg']};   background:{P['red_bg']}; }}
      .v-hold        {{ color:{P['amber_fg']}; background:{P['amber_bg']}; }}
      .v-default     {{ color:{P['neutral_fg']}; background:{P['neutral_bg']}; }}
      .meta-pill     {{ display:inline-block; padding:3px 10px; border-radius:999px;
                        font-family:'JetBrains Mono', monospace; font-size:11px;
                        background:{P['neutral_bg']}; color:{P['neutral_fg']}; margin-left:6px; }}
      .conflict-pill {{ display:block; margin-top:8px; padding:5px 10px; border-radius:6px;
                        font-size:12px; font-weight:600; color:{P['amber_fg']};
                        background:{P['amber_bg']}; border:1px solid {P['amber_fg']}; }}
      .net-pos {{ color:{P['green_fg']}; font-weight:700; }}
      .net-neg {{ color:{P['red_fg']};   font-weight:700; }}
      .net-zero{{ color:{P['neutral_fg']}; font-weight:700; }}
      .fund-row {{
        font-family: 'JetBrains Mono', monospace; font-size: 12px; color:{P['muted']};
        background: {P['fund_bg']}; padding: 8px 12px; border-radius: 8px;
        margin-top: 6px;
      }}
      .fund-row b {{ color:{P['strong_b']}; }}
      .trade-plan {{
        font-family: 'JetBrains Mono', monospace; font-size: 12px; color:{P['tp_fg']};
        background: {P['tp_bg']}; padding: 10px 12px; border-radius: 8px;
        margin-top: 6px; line-height: 1.65;
      }}
      .trade-plan b           {{ color:{P['strong_b']}; }}
      .trade-plan .tp-entry   {{ color:{P['green_fg']}; font-weight:700; }}
      .trade-plan .tp-sl      {{ color:{P['red_fg']};   font-weight:700; }}
      .trade-plan .tp-target  {{ color:{P['blue_fg']};  font-weight:700; }}
      .trade-plan .tp-row     {{ display:flex; flex-wrap:wrap; gap:14px 18px; }}
      .trade-plan .tp-cell    {{ white-space:nowrap; }}
      .trade-plan .tp-anchor  {{ color:{P['tp_dim']}; font-size:11px; margin-top:6px;
                                 padding-top:6px; border-top:1px dashed {P['border']}; }}
      .group-head-pro {{ color:{P['green_fg']}; font-size: 11px; font-weight:700; letter-spacing:.08em;
                         text-transform:uppercase; margin-top:10px; }}
      .group-head-con {{ color:{P['red_fg']};   font-size: 11px; font-weight:700; letter-spacing:.08em;
                         text-transform:uppercase; margin-top:10px; }}
      .pro-li {{ background:{P['green_bg']}; padding: 4px 10px; border-radius:6px;
                 margin: 4px 0; font-size: 13px; color:{P['fg']}; }}
      .con-li {{ background:{P['red_bg']};   padding: 4px 10px; border-radius:6px;
                 margin: 4px 0; font-size: 13px; color:{P['fg']}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def _toggle_theme() -> None:
    """Flip light ↔ dark and let Streamlit rerun to repaint the page."""
    st.session_state["theme"] = "light" if DARK else "dark"

# ─────────────────────────────────────────── Parser ────────────────────────────
SUMMARY_PATH = Path(__file__).parent / "stocks_in_trend_summary.txt"
BULK_DEALS_PATH = Path(__file__).parent / "bulk_deals.csv"
POSITIONS_PATH = Path(__file__).parent / "positions.json"

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
        """Pull the BUY trade-management levels from the
        'TRADE PLAN (BUY):' block if present.

        Current format (ChartPrime swing fib, 5 targets):
            - Entry zone (probable): above ₹X
            - Strict stop-loss:      ₹X
            - Best stop-loss:        ₹X
            - Target-1 (50.0%):      ₹X      (retracement)
            - Target-2 (61.8%):      ₹X      (retracement)
            - Target-3 (150%):       ₹X      (extension)
            - Target-4 (161.8%):     ₹X      (extension)
            - Target-5 (261.8%):     ₹X      (extension)
            - Swing anchor:          low ₹A  ↔  high ₹B

        Returns empty strings for any field not present so the renderer
        can gracefully degrade for older summary files.
        """
        out = {
            "entry": "",
            "strict_sl": "", "best_sl": "",
            "target_1": "", "target_2": "",
            "target_3": "", "target_4": "", "target_5": "",
            "swing_low": "", "swing_high": "",
        }
        price = r"(₹[\d.,]+)"

        # Entry zone
        m = re.search(rf"Entry zone\s*\(probable\):\s+above\s+{price}", block)
        if m:
            out["entry"] = m.group(1)

        # Stop-losses — plain price, no fib annotation
        m = re.search(rf"Strict stop-loss:\s+{price}", block)
        if m:
            out["strict_sl"] = m.group(1)

        m = re.search(rf"Best stop-loss:\s+{price}", block)
        if m:
            out["best_sl"] = m.group(1)

        # Targets — labels carry the ratio in parens; capture the price.
        for n in range(1, 6):
            m = re.search(
                rf"Target-{n}\s*(?:\([^)]+\))?:\s+{price}", block)
            if m:
                out[f"target_{n}"] = m.group(1)

        # Swing anchor: "low ₹X  ↔  high ₹Y"
        m = re.search(
            rf"Swing anchor:\s+low\s+{price}\s+.+?\s+high\s+{price}", block)
        if m:
            out["swing_low"] = m.group(1)
            out["swing_high"] = m.group(2)

        return out

    fund_match = re.search(r"FUNDAMENTALS \(screener\.in\):\s+(.+)", block)
    url_match = re.search(r"(https?://www\.screener\.in/\S+)", block)
    fund_text = fund_match.group(1).strip() if fund_match else ""

    # PEG / PEGY — pulled from the FUNDAMENTALS one-liner so the Trades
    # table can render numeric columns instead of dumping the raw string.
    # Emitted format:  "... | PEG 1.23 (5Y) | PEGY 0.95 | ..."
    def _grab_float(pattern: str, src: str) -> float | None:
        m = re.search(pattern, src)
        if not m:
            return None
        try:
            return float(m.group(1))
        except (TypeError, ValueError):
            return None

    peg_val    = _grab_float(r"\bPEG\s+([\-0-9.]+)",  fund_text)
    pegy_val   = _grab_float(r"\bPEGY\s+([\-0-9.]+)", fund_text)
    peg_src_m  = re.search(r"\bPEG\s+[\-0-9.]+\s*\((\w+)\)", fund_text)
    peg_source = peg_src_m.group(1) if peg_src_m else ""

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
        "fundamentals":    fund_text,
        "peg":             peg_val,
        "pegy":            pegy_val,
        "peg_source":      peg_source,
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
title_col, toggle_col = st.columns([8, 1])
with title_col:
    st.markdown("# 📈 Stocks in Trend")
    st.caption(
        f"NSE bhavcopy analysis · {data['generated'] or 'date not detected'} · "
        "Pure-on-Volume + screener.in fundamentals"
    )
with toggle_col:
    st.markdown('<div class="theme-toggle">', unsafe_allow_html=True)
    st.button(
        "☀️ Light" if DARK else "🌙 Dark",
        key="theme_toggle_btn",
        on_click=_toggle_theme,
        use_container_width=True,
        help="Toggle dark / light theme",
    )
    st.markdown('</div>', unsafe_allow_html=True)

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
    """Render the BUY trade-management block: entry, strict & best
    stops, five fib targets (T1/T2 retracements + T3/T4/T5 extensions),
    and the swing-anchor context line."""
    if not tp or not any(tp.values()):
        return

    def _cell(label: str, price: str, klass: str) -> str:
        price = price or "—"
        return (
            f'<span class="tp-cell"><b>{label}</b> '
            f'<span class="{klass}">{price}</span></span>'
        )

    row_cells = [
        _cell("Entry &gt;", tp.get("entry", ""), "tp-entry"),
        _cell("Strict SL", tp.get("strict_sl", ""), "tp-sl"),
        _cell("Best SL",   tp.get("best_sl", ""),   "tp-sl"),
    ]
    # Only render the targets that the pipeline emitted — by design
    # the pipeline now filters out any target at or below the entry
    # zone, so the dashboard simply shows whatever is present.
    target_labels = [
        ("target_1", "T1 (50.0%)"),
        ("target_2", "T2 (61.8%)"),
        ("target_3", "T3 (150%)"),
        ("target_4", "T4 (161.8%)"),
        ("target_5", "T5 (261.8%)"),
    ]
    for key, label in target_labels:
        if tp.get(key):
            row_cells.append(_cell(label, tp[key], "tp-target"))

    anchor_html = ""
    if tp.get("swing_low") and tp.get("swing_high"):
        anchor_html = (
            f'<div class="tp-anchor">Swing anchor &nbsp;·&nbsp; '
            f'low <b>{tp["swing_low"]}</b> &nbsp;↔&nbsp; '
            f'high <b>{tp["swing_high"]}</b></div>'
        )

    st.markdown(
        '<div class="trade-plan">'
        f'<div class="tp-row">{"".join(row_cells)}</div>'
        f'{anchor_html}'
        '</div>',
        unsafe_allow_html=True,
    )


def render_card(stock: dict, kind: str) -> None:
    pct = stock["change_pct"]
    pct_str = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
    # Streamlit default: positive delta is green, negative is red.
    # Keep it that way — "inverse" would flip colors which is misleading
    # for stock price changes.
    pct_color = "normal"

    verdict = stock["verdict"] or stock["bias"].replace("_", " ")
    verdict_class = VERDICT_CLASS.get(verdict.upper().strip(), "v-default")

    net = stock["net"]
    net_class = "net-pos" if net > 0 else ("net-neg" if net < 0 else "net-zero")
    net_str = f"+{net}" if net > 0 else f"{net}"

    # The tab a card sits under (`kind`, "buy" or "sell") reflects only
    # *today's* raw volume-day classification (Pure_on_Volume breakout vs.
    # HV-distribution day). The `verdict` badge is a separate scorecard —
    # technical bias + net pros/cons from signals & fundamentals — and can
    # legitimately disagree (e.g. a bearish-volume day on an otherwise
    # strong stock). Flag it explicitly instead of leaving it looking like
    # a contradiction.
    verdict_upper = verdict.upper()
    conflict = (
        (kind == "buy" and "SELL" in verdict_upper)
        or (kind == "sell" and "BUY" in verdict_upper)
    )

    with st.container(border=True):
        h1, h2 = st.columns([3, 3])
        with h1:
            st.markdown(
                f'<div class="stock-symbol">{stock["symbol"]}</div>'
                f'<div class="stock-name">{stock["name"]}</div>',
                unsafe_allow_html=True,
            )
        with h2:
            st.metric("Close", f"₹{stock['price']:,.2f}", pct_str, delta_color=pct_color)

        # PEG / PEGY chips — colour-coded by value band. Only rendered
        # when the pipeline could compute them (needs positive PE and
        # positive growth from screener.in).
        peg_html  = ""
        pegy_html = ""

        def _peg_band(v: float | None) -> tuple[str, str]:
            """Return (colour_class, formatted_label) for a PEG/PEGY value.
              <1.0  → green   (attractive)
              1–1.5 → blue    (fair)
              1.5–2 → amber   (fully valued)
              >2.0  → red     (expensive)
            """
            if v is None:
                return ("", "")
            if v < 1.0:
                cls = "net-pos"      # green
            elif v < 1.5:
                cls = "v-default"    # neutral / blue
            elif v < 2.0:
                cls = "net-zero"     # amber
            else:
                cls = "net-neg"      # red
            return (cls, f"{v:.2f}")

        p_cls, p_lbl = _peg_band(stock.get("peg"))
        y_cls, y_lbl = _peg_band(stock.get("pegy"))
        if p_lbl:
            src = stock.get("peg_source") or ""
            src_suffix = f" ({src})" if src else ""
            peg_html = (
                f'<span class="meta-pill" title="P/E ÷ Growth% — '
                f'&lt;1 undervalued · 1–1.5 fair · &gt;2 premium">'
                f'PEG <span class="{p_cls}">{p_lbl}</span>{src_suffix}</span>'
            )
        if y_lbl:
            pegy_html = (
                f'<span class="meta-pill" title="Peter Lynch\'s PEGY = '
                f'P/E ÷ (Growth% + DivYield%) — credits dividend income">'
                f'PEGY <span class="{y_cls}">{y_lbl}</span></span>'
            )

        st.markdown(
            f'<span class="verdict-badge {verdict_class}">{verdict}</span>'
            f'<span class="meta-pill">bias {stock["bias"]}</span>'
            f'<span class="meta-pill">net <span class="{net_class}">{net_str}</span></span>'
            f'{peg_html}{pegy_html}',
            unsafe_allow_html=True,
        )

        if conflict:
            st.markdown(
                '<span class="conflict-pill">⚠ Signal conflict — bucketed under '
                f'{kind.upper()} by today\'s raw volume action, but the '
                f'verdict says {verdict}. These measure different things; '
                'read both before acting.</span>',
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


# ─────────────────────────────────────────── Bulk deals loader ────────────────
@st.cache_data(show_spinner=False, ttl=900)
def load_bulk_deals() -> pd.DataFrame | None:
    """Load the bulk-deals CSV produced by the pipeline. Returns None if the
    file is missing, unreadable, or empty so the tab can show a friendly
    message instead of crashing."""
    if not BULK_DEALS_PATH.exists():
        return None
    try:
        df = pd.read_csv(BULK_DEALS_PATH)
    except Exception:
        return None
    if df.empty:
        return None
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "buy_sell" in df.columns:
        df["buy_sell"] = df["buy_sell"].astype(str).str.strip().str.upper()
    return df


# ─────────────────────────────────────────── Positions loader ─────────────────
@st.cache_data(show_spinner=False, ttl=300)
def load_positions() -> list[dict]:
    """Load the BUY position ledger written by the pipeline.

    Returns [] if the file is missing or unreadable so the tab can render
    a friendly empty state rather than crashing.
    """
    if not POSITIONS_PATH.exists():
        return []
    try:
        raw = POSITIONS_PATH.read_text(encoding="utf-8")
    except Exception:
        return []
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _tranches_summary(p: dict) -> tuple[str, int, int]:
    """Returns (display_str, exited_qty_pct, open_qty_pct). Wave 1 v2
    positions carry a `tranches: [{name, qty_pct, status, exit_price}]`
    list; legacy v1 records auto-migrate to a single 100 % `FULL`
    tranche in the pipeline loader."""
    tr = p.get("tranches") or []
    if not tr:
        return ("", 0, 100)
    parts = []
    exited_qty = 0
    open_qty = 0
    for t in tr:
        name = t.get("name") or "?"
        qp = int(t.get("qty_pct") or 0)
        status = t.get("status") or "open"
        if status == "exited":
            xp = t.get("exit_price")
            xp_str = f"@₹{xp:,.2f}" if isinstance(xp, (int, float)) else ""
            parts.append(f"{name}:{qp}% ✓{xp_str}")
            exited_qty += qp
        else:
            parts.append(f"{name}:{qp}%")
            open_qty += qp
    return (" · ".join(parts), exited_qty, open_qty)


def _positions_to_frame(positions: list[dict], status: str) -> pd.DataFrame:
    """Flatten the JSON position records into a tidy DataFrame for the
    selected status ('open', 'pending', 'closed')."""
    rows = []
    for p in positions:
        if p.get("status") != status:
            continue
        targets = p.get("targets") or []
        already_hit = set(p.get("hit_targets") or [])
        # Annotate hit targets with a check; unhit stay plain.
        target_prices = " · ".join(
            (
                f"{t.get('name')}:₹{t.get('price'):,.2f}"
                + (" ✓" if t.get("name") in already_hit else "")
            )
            for t in targets if t.get("price") is not None
        )
        hit_str = ", ".join(sorted(already_hit)) if already_hit else ""
        tr_str, exited_pct, open_pct = _tranches_summary(p)
        rows.append({
            "Symbol":     p.get("symbol"),
            "Name":       p.get("name"),
            "V":          p.get("strategy_version") or 1,
            "Score":      p.get("score_total"),
            "R/R":        p.get("reward_risk"),
            "PEG":        p.get("peg_at_entry"),
            "PEGY":       p.get("pegy_at_entry"),
            "PEG src":    p.get("peg_source") or "",
            "Suggested":  p.get("suggested_on"),
            "Entry":      p.get("entry"),
            "Fill ≥":     p.get("fill_trigger"),
            "Fill date":  p.get("fill_date"),
            "Fill px":    p.get("fill_price"),
            "Stop loss":  p.get("stoploss"),
            "SL src":     p.get("stoploss_source") or "",
            "Targets":    target_prices,
            "Hit":        hit_str,
            "Tranches":   tr_str,
            "Out %":      exited_pct,
            "Open %":     open_pct,
            "Exit date":  p.get("exit_date"),
            "Exit px":    p.get("exit_price"),
            "Exit why":   p.get("exit_reason"),
            "Days":       p.get("days_held"),
            "P&L %":      p.get("pnl_pct"),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────── Trades table helper ───────────────
_PRICE_RE = re.compile(r"[₹,\s]")


def _price_to_float(s) -> float | None:
    """Convert a '₹1,234.56' style string to float; return None on miss."""
    if not s:
        return None
    try:
        return float(_PRICE_RE.sub("", str(s)))
    except (TypeError, ValueError):
        return None


def _signals_to_trades_frame(signals: list[dict], side: str) -> pd.DataFrame:
    """Build a compact, tabular view of today's BUY/SELL candidates with
    trade-plan levels. One row per stock — designed for fast scanning
    (sortable columns, no card scrolling).

    `side` is 'buy' or 'sell'. SELL rows omit trade-plan columns since
    the pipeline only emits a plan for BUY signals.
    """
    rows = []
    for s in signals:
        tp = s.get("trade_plan") or {}
        # Wave 1: score + R/R may be in the parsed summary (if the pipeline
        # exposes them) or absent (older summary shapes) — fall back to None.
        rows.append({
            "Symbol":   s.get("symbol", ""),
            "Name":     s.get("name", ""),
            "Close":    s.get("price"),
            "% chg":    s.get("change_pct"),
            "Verdict":  s.get("verdict") or s.get("bias", ""),
            "Bias":     s.get("bias", ""),
            "Net":      s.get("net", 0),
            # Wave 1 diagnostic columns — surface when present
            "Score":    s.get("score_total"),
            "R/R":      s.get("reward_risk"),
            # PEG  = P/E ÷ Growth% (5Y cascade → 3Y → TTM). Informational.
            # PEGY = P/E ÷ (Growth% + DivYield%) — Peter Lynch's variant.
            "PEG":      s.get("peg"),
            "PEGY":     s.get("pegy"),
            "PEG src":  s.get("peg_source") or "",
            "Vol":      s.get("score_vol"),
            "Deliv":    s.get("score_delivery"),
            "Trend":    s.get("score_trend"),
            "RS":       s.get("score_rs"),
            "Mom":      s.get("score_momentum"),
            "Entry":    _price_to_float(tp.get("entry")),
            "Strict SL":_price_to_float(tp.get("strict_sl")),
            "Best SL":  _price_to_float(tp.get("best_sl")),
            "T1":       _price_to_float(tp.get("target_1")),
            "T2":       _price_to_float(tp.get("target_2")),
            "T3":       _price_to_float(tp.get("target_3")),
            "T4":       _price_to_float(tp.get("target_4")),
            "T5":       _price_to_float(tp.get("target_5")),
            "Side":     side.upper(),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────── Tabs ──────────────────────────────
positions_data = load_positions()
n_open    = sum(1 for p in positions_data if p.get("status") == "open")
n_pending = sum(1 for p in positions_data if p.get("status") == "pending")
n_closed  = sum(1 for p in positions_data if p.get("status") == "closed")
n_trades  = len(data["buys"]) + len(data["sells"])

buy_tab, sell_tab, trades_tab, pos_tab, bulk_tab, raw_tab = st.tabs(
    [
        f"💚  BUY  ({len(data['buys'])})",
        f"❤️  SELL  ({len(data['sells'])})",
        f"📊  Trades  ({n_trades})",
        f"📓  Positions  ({n_open + n_pending} live · {n_closed} closed)",
        "🧾  Bulk Deals",
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

with trades_tab:
    if not data["buys"] and not data["sells"]:
        st.info("No trade candidates parsed from the summary.")
    else:
        st.caption(
            "Compact table view of today's signals — sortable, scannable, "
            "and friendly to copy into a watchlist. BUY rows include the "
            "full trade-plan ladder (Entry, Strict SL, Best SL, T1–T5); "
            "SELL rows show price/verdict only since the pipeline doesn't "
            "emit a plan for shorts."
        )

        side_filter = st.radio(
            "Side",
            ["Both", "BUY only", "SELL only"],
            index=0,
            horizontal=True,
            key="trades_side_filter",
        )

        frames: list[pd.DataFrame] = []
        if side_filter in ("Both", "BUY only") and data["buys"]:
            frames.append(_signals_to_trades_frame(data["buys"], "buy"))
        if side_filter in ("Both", "SELL only") and data["sells"]:
            frames.append(_signals_to_trades_frame(data["sells"], "sell"))

        if not frames:
            st.info("Nothing to show for the selected side.")
        else:
            trades_df = pd.concat(frames, ignore_index=True)

            # Column order — Side first when both are visible so BUY/SELL
            # rows are easy to tell apart, then identity, then trade plan.
            base_cols = [
                "Side", "Symbol", "Name", "Close", "% chg",
                "Verdict", "Bias", "Net", "PEG", "PEGY",
                "Entry", "Strict SL", "Best SL",
                "T1", "T2", "T3", "T4", "T5",
            ]
            if side_filter != "Both":
                # Drop the Side column when filtered to a single side.
                base_cols = [c for c in base_cols if c != "Side"]
            view = trades_df[[c for c in base_cols if c in trades_df.columns]]

            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Close":     st.column_config.NumberColumn(format="₹%.2f"),
                    "% chg":     st.column_config.NumberColumn(format="%+.2f %%"),
                    "Net":       st.column_config.NumberColumn(format="%+d"),
                    "PEG":       st.column_config.NumberColumn(format="%.2f",
                                    help="Price-to-Earnings-Growth = P/E ÷ "
                                         "5Y Compounded Profit Growth% (cascades "
                                         "to 3Y then TTM if 5Y missing). "
                                         "<1 = undervalued vs growth · "
                                         "1–1.5 = fair · >2 = premium. "
                                         "Blank = loss-making, no growth data, "
                                         "or PE unavailable."),
                    "PEGY":      st.column_config.NumberColumn(format="%.2f",
                                    help="Peter Lynch's PEGY = P/E ÷ "
                                         "(Growth% + DivYield%). Rewards "
                                         "high-dividend payers — a 3% "
                                         "yielder on 15% growth uses 18 in "
                                         "the denominator vs PEG's 15. "
                                         "<1 = attractive · >2 = expensive."),
                    "Entry":     st.column_config.NumberColumn(format="₹%.2f"),
                    "Strict SL": st.column_config.NumberColumn(format="₹%.2f"),
                    "Best SL":   st.column_config.NumberColumn(format="₹%.2f"),
                    "T1":        st.column_config.NumberColumn(format="₹%.2f"),
                    "T2":        st.column_config.NumberColumn(format="₹%.2f"),
                    "T3":        st.column_config.NumberColumn(format="₹%.2f"),
                    "T4":        st.column_config.NumberColumn(format="₹%.2f"),
                    "T5":        st.column_config.NumberColumn(format="₹%.2f"),
                },
            )

            st.download_button(
                "Download trades.csv",
                data=trades_df.to_csv(index=False).encode("utf-8"),
                file_name="trades.csv",
                mime="text/csv",
            )

with pos_tab:
    if not positions_data:
        st.info(
            "No positions tracked yet. The pipeline writes "
            "`positions.json` next to this script on every run — "
            "fresh BUY signals will start appearing here once the next "
            "daily run completes."
        )
    else:
        st.caption(
            f"**{n_open}** open · **{n_pending}** pending fill · "
            f"**{n_closed}** closed. A signal becomes *open* the day "
            "price trades ≥ 1.2 % above the suggested entry. Once open, "
            "each target the price reaches **trails the stop loss up** "
            "to that target (T1 → T2 → T3 → …) so winners can run with "
            "locked-in gains. The position closes when the trailed stop "
            "is hit, or hits a hard ceiling at **+66 % of fill price**. "
            "Missing stop losses are backfilled on the **weekly** "
            "timeframe at the 0.786 swing-fib retracement."
        )

        # ── Open positions ──────────────────────────────────────────────
        st.markdown("### 🟢 Open (filled, still live)")
        open_df = _positions_to_frame(positions_data, "open")
        if open_df.empty:
            st.caption("No open positions right now.")
        else:
            open_cols = [
                "Symbol", "Name", "V", "Score", "R/R", "PEG", "PEGY",
                "Suggested", "Entry",
                "Fill date", "Fill px", "Stop loss", "SL src",
                "Targets", "Hit", "Tranches", "Out %", "Days", "P&L %",
            ]
            view = open_df[[c for c in open_cols if c in open_df.columns]]
            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Entry":     st.column_config.NumberColumn(format="₹%.2f"),
                    "Fill px":   st.column_config.NumberColumn(format="₹%.2f"),
                    "Stop loss": st.column_config.NumberColumn(format="₹%.2f"),
                    "Days":      st.column_config.NumberColumn(format="%d"),
                    "Score":     st.column_config.NumberColumn(format="%.0f",
                                    help="Weighted 0–100 (Wave 1 scoring: "
                                         "vol 25 + delivery 15 + trend 25 + "
                                         "RS 15 + momentum 15 + sector 5). "
                                         "≥ 80 = passes Strong_Buy gate."),
                    "R/R":       st.column_config.NumberColumn(format="%.2f",
                                    help="(T1 - entry) / (entry - dynamic SL); "
                                         "Wave 1 requires ≥ 3.0"),
                    "PEG":       st.column_config.NumberColumn(format="%.2f",
                                    help="P/E ÷ Growth% (frozen at entry). "
                                         "<1 undervalued · 1–1.5 fair · "
                                         ">2 premium. Blank = loss-making or "
                                         "growth data missing."),
                    "PEGY":      st.column_config.NumberColumn(format="%.2f",
                                    help="Peter Lynch's PEGY = P/E ÷ "
                                         "(Growth% + DivYield%). Credits "
                                         "dividend income — usually lower "
                                         "than PEG for high-payout stocks. "
                                         "<1 = attractive."),
                    "Out %":     st.column_config.NumberColumn(format="%d %%",
                                    help="Percent of qty already exited via "
                                         "partial-target tranches"),
                    "V":         st.column_config.NumberColumn(format="%d",
                                    help="Strategy version — 2 = Wave 1 rules "
                                         "(trend + score + tranches); 1 = legacy"),
                    "P&L %":     st.column_config.NumberColumn(format="%.2f %%"),
                },
            )

        # ── Pending positions ───────────────────────────────────────────
        st.markdown("### 🟡 Pending (waiting for 1.2 % confirmation)")
        pend_df = _positions_to_frame(positions_data, "pending")
        if pend_df.empty:
            st.caption("No pending signals.")
        else:
            pend_cols = [
                "Symbol", "Name", "V", "Score", "R/R", "PEG", "PEGY",
                "Suggested", "Entry",
                "Fill ≥", "Stop loss", "SL src", "Targets", "Tranches",
            ]
            view = pend_df[[c for c in pend_cols if c in pend_df.columns]]
            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Entry":     st.column_config.NumberColumn(format="₹%.2f"),
                    "Fill ≥":    st.column_config.NumberColumn(format="₹%.2f"),
                    "Stop loss": st.column_config.NumberColumn(format="₹%.2f"),
                    "Score":     st.column_config.NumberColumn(format="%.0f"),
                    "R/R":       st.column_config.NumberColumn(format="%.2f"),
                    "PEG":       st.column_config.NumberColumn(format="%.2f",
                                    help="P/E ÷ Growth% (5Y cascade)"),
                    "PEGY":      st.column_config.NumberColumn(format="%.2f",
                                    help="P/E ÷ (Growth% + DivYield%) — "
                                         "Peter Lynch's variant that credits "
                                         "dividend income. <1 = attractive."),
                    "V":         st.column_config.NumberColumn(format="%d"),
                },
            )

        # ── Closed positions ────────────────────────────────────────────
        st.markdown("### ⚪ Closed (target hit or stopped out)")
        closed_df = _positions_to_frame(positions_data, "closed")
        if closed_df.empty:
            st.caption("No closed positions yet.")
        else:
            closed_cols = [
                "Symbol", "Name", "V", "Score", "R/R", "Suggested", "Entry",
                "Fill date", "Fill px", "Exit date", "Exit px",
                "Exit why", "Tranches", "Days", "P&L %",
            ]
            view = closed_df[[c for c in closed_cols if c in closed_df.columns]]
            # Sort by most recent exit
            if "Exit date" in view.columns:
                view = view.sort_values("Exit date", ascending=False)
            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Entry":   st.column_config.NumberColumn(format="₹%.2f"),
                    "Fill px": st.column_config.NumberColumn(format="₹%.2f"),
                    "Exit px": st.column_config.NumberColumn(format="₹%.2f"),
                    "Days":    st.column_config.NumberColumn(format="%d"),
                    "P&L %":   st.column_config.NumberColumn(format="%+.2f %%"),
                },
            )

            # Quick summary stats
            wins   = closed_df[closed_df["P&L %"].fillna(0) > 0]
            losses = closed_df[closed_df["P&L %"].fillna(0) <= 0]
            if len(closed_df) > 0:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Win rate",
                          f"{(len(wins) / len(closed_df)) * 100:.1f}%")
                k2.metric("Avg P&L",
                          f"{closed_df['P&L %'].mean():+.2f}%")
                k3.metric("Best",
                          f"{closed_df['P&L %'].max():+.2f}%")
                k4.metric("Worst",
                          f"{closed_df['P&L %'].min():+.2f}%")

        st.download_button(
            "Download positions.json",
            data=POSITIONS_PATH.read_text(encoding="utf-8")
                 if POSITIONS_PATH.exists() else "[]",
            file_name="positions.json",
            mime="application/json",
        )

with bulk_tab:
    deals = load_bulk_deals()
    if deals is None or deals.empty:
        st.info(
            "Bulk deals data not yet available. The pipeline writes "
            "`bulk_deals.csv` next to this script — run the daily pipeline "
            "(or wait for the next scheduled run) to populate it."
        )
    else:
        side = st.selectbox(
            "Side",
            ["All", "BUY", "SELL"],
            index=0,
            key="bulk_deals_side",
            help="Filter the most recent 150 NSE bulk deals by side.",
        )
        view = deals if side == "All" else deals[deals["buy_sell"] == side]
        view = view.copy()

        if "date" in view.columns:
            view["date"] = view["date"].dt.strftime("%d-%b-%Y")

        display_map = {
            "date":     "Date",
            "symbol":   "Symbol",
            "name":     "Name",
            "client":   "Client",
            "buy_sell": "Side",
            "quantity": "Quantity",
            "price":    "Price (₹)",
            "value":    "Value (₹)",
            "remarks":  "Remarks",
        }
        keep = [c for c in display_map if c in view.columns]
        view = view[keep].rename(columns=display_map)

        st.caption(
            f"Showing **{len(view)}** of **{len(deals)}** most recent bulk "
            "deals from NSE (top 150, last ~30 days). "
            "Source: nseindia.com/report-detail/display-bulk-and-block-deals"
        )

        col_cfg: dict = {}
        if "Quantity" in view.columns:
            col_cfg["Quantity"] = st.column_config.NumberColumn(format="%d")
        if "Price (₹)" in view.columns:
            col_cfg["Price (₹)"] = st.column_config.NumberColumn(format="₹%.2f")
        if "Value (₹)" in view.columns:
            col_cfg["Value (₹)"] = st.column_config.NumberColumn(format="₹%.0f")

        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
        )

        st.download_button(
            "Download bulk_deals.csv",
            data=deals.to_csv(index=False).encode("utf-8"),
            file_name="bulk_deals.csv",
            mime="text/csv",
        )

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
    "**Methodology (Wave 1 – v2).** BUY signals require ALL of: "
    "HVQ/HVY/HVE volume breakout · trend (close > EMA-50, EMA-50 > EMA-200, "
    "ADX ≥ 20, weekly bar bullish) · volume quality (vol ≥ 2.5× 20-day avg, "
    "delivery ≥ 40 % and rising, OBV new 20-day high, CMF > 0.10) · not "
    "extended (gap-up ≤ 5 %, ATR ≤ 8 % of price, close ≤ 20-EMA × 1.15) · "
    "R/R ≥ 3.0 vs T1 · weighted score ≥ 80/100 (vol 25 · delivery 15 · trend "
    "25 · RS-rank proxy 15 · momentum 15 · sector 5). "
    "**Dynamic SL** = max(entry − ATR-14 × 1.5, swing_low, weekly-fib-0.786). "
    "**Partial-exit tranches:** 25 % at T1 (SL → breakeven), 25 % at T2 "
    "(SuperTrend(10, 3) trail activates), 30 % at T3, 20 % trails on "
    "SuperTrend. All exits capped at fill × 1.66 (+66 %). Legacy trades "
    "(strategy_version = 1) keep their original one-shot exit rules."
)
