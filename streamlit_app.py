"""
Stocks in Trend — Streamlit dashboard.
Reads `stocks_in_trend_summary.txt` next to this file.
Works with any "Top N BUY / Top N SELL" section headers.
"""

from __future__ import annotations
import re
from pathlib import Path
import streamlit as st

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Stocks in Trend", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  .block-container{padding-top:2rem;padding-bottom:4rem;max-width:1280px}
  .card-header{display:flex;justify-content:space-between;align-items:flex-start;
               gap:12px;flex-wrap:nowrap}
  .stock-symbol{font-family:'JetBrains Mono',ui-monospace,monospace;
                font-weight:700;font-size:18px;letter-spacing:-.01em}
  .stock-name{color:#94a3b8;font-size:13px;margin-top:2px}
  .price-block{text-align:right;flex-shrink:0;min-width:130px}
  .price-label{color:#94a3b8;font-size:11px;text-transform:uppercase;
               letter-spacing:.07em;margin-bottom:2px}
  .price-value{font-family:'JetBrains Mono',ui-monospace,monospace;
               font-weight:700;font-size:20px;white-space:nowrap}
  .pct-up  {display:inline-block;padding:2px 9px;border-radius:999px;
            font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;
            color:#15803d;background:rgba(34,197,94,.12)}
  .pct-down{display:inline-block;padding:2px 9px;border-radius:999px;
            font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;
            color:#b91c1c;background:rgba(239,68,68,.12)}
  .pct-flat{display:inline-block;padding:2px 9px;border-radius:999px;
            font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;
            color:#475569;background:rgba(148,163,184,.12)}
  .verdict-badge{display:inline-block;padding:3px 10px;border-radius:999px;
                 font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
                 letter-spacing:.04em;border:1px solid currentColor}
  .v-sb {color:#15803d;background:rgba(34,197,94,.10)}
  .v-bl {color:#15803d;background:rgba(34,197,94,.06)}
  .v-ss {color:#b91c1c;background:rgba(239,68,68,.10)}
  .v-sl {color:#b91c1c;background:rgba(239,68,68,.06)}
  .v-ho {color:#a16207;background:rgba(234,179,8,.10)}
  .v-de {color:#475569;background:rgba(148,163,184,.10)}
  .meta-pill{display:inline-block;padding:3px 10px;border-radius:999px;
             font-family:'JetBrains Mono',monospace;font-size:11px;
             background:rgba(148,163,184,.12);color:#475569;margin-left:6px}
  .net-pos{color:#15803d;font-weight:700}
  .net-neg{color:#b91c1c;font-weight:700}
  .net-zero{color:#475569;font-weight:700}
  .fund-row{font-family:'JetBrains Mono',monospace;font-size:12px;color:#475569;
            background:rgba(148,163,184,.08);padding:8px 12px;border-radius:8px;margin-top:6px}
  .fund-row b{color:#0f172a}
  .gh-pro{color:#15803d;font-size:11px;font-weight:700;letter-spacing:.08em;
          text-transform:uppercase;margin-top:10px}
  .gh-con{color:#b91c1c;font-size:11px;font-weight:700;letter-spacing:.08em;
          text-transform:uppercase;margin-top:10px}
  .pro-li{background:rgba(34,197,94,.10);padding:4px 10px;border-radius:6px;margin:4px 0;font-size:13px}
  .con-li{background:rgba(239,68,68,.10);padding:4px 10px;border-radius:6px;margin:4px 0;font-size:13px}
</style>
""", unsafe_allow_html=True)

# ── constants ────────────────────────────────────────────────────────────────
VERDICT_CSS = {
    "STRONG BUY":   "v-sb", "BUY-LEAN": "v-bl", "BUY": "v-bl",
    "STRONG SELL":  "v-ss", "SELL-LEAN": "v-sl", "SELL": "v-sl",
    "HOLD / MIXED": "v-ho",
}
SUMMARY_PATH = Path(__file__).parent / "stocks_in_trend_summary.txt"


# ── parser ───────────────────────────────────────────────────────────────────
def split_blocks(text: str) -> list[str]:
    """Split text into per-stock blocks on bullet (•) lines."""
    blocks, cur = [], []
    for line in text.splitlines():
        if re.match(r"\s*•\s+\S", line):
            if cur:
                blocks.append("\n".join(cur))
            cur = [line]
        elif cur:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return [b for b in blocks if b.strip()]


def grab_list(label: str, block: str) -> list[str]:
    m = re.search(rf"{re.escape(label)}\s*\n((?:\s+-\s.+\n?)+)", block)
    if not m:
        return []
    return [re.sub(r"^\s*-\s+", "", l).strip()
            for l in m.group(1).splitlines() if l.strip().startswith("-")]


def parse_block(block: str) -> dict | None:
    head = re.match(
        r"\s*•\s+(\S+)\s+\((.+?)\)\s+close\s+₹([\d.]+)\s+([+-]?[\d.]+)%\s+bias\s+(\S+)",
        block)
    if not head:
        return None
    verdict_m = re.search(
        r"→\s+(.+?)\s+\(tech=(\S+),\s*signal net\s+([+-]?\d+)\)", block)
    fund_m = re.search(r"FUNDAMENTALS \(screener\.in\):\s+(.+)", block)
    url_m  = re.search(r"(https?://www\.screener\.in/\S+)", block)
    bias   = head.group(5)
    return {
        "symbol":        head.group(1),
        "name":          head.group(2).strip(),
        "price":         float(head.group(3)),
        "change_pct":    float(head.group(4)),
        "bias":          bias,
        "is_sell":       "SELL" in bias and "BUY" not in bias,
        "verdict":       verdict_m.group(1).strip() if verdict_m else "",
        "net":           int(verdict_m.group(3)) if verdict_m else 0,
        "signal_pros":   grab_list("PROS (signals):", block),
        "signal_cons":   grab_list("CONS (signals):", block),
        "screener_pros": grab_list("PROS (screener.in):", block),
        "screener_cons": grab_list("CONS (screener.in):", block),
        "fundamentals":  fund_m.group(1).strip() if fund_m else "",
        "url":           url_m.group(1) if url_m else "",
    }


def parse_file(text: str) -> dict:
    gen_m   = re.search(r"generated\s+(.+)$", text, flags=re.M)
    hits_m  = re.search(r"Pure_on_Volume hits \(BUY\):\s+(\d+)", text)
    rec_m   = re.search(r"Recommendations:\s+(\d+)\s+BUY\s+\+\s+(\d+)\s+SELL", text)

    # ── section extraction  (works for any "Top N" number) ──────────────────
    buy_m = re.search(
        r"Top \d+ BUY candidates[^:]*:\s*\n-+\n(.*?)(?=\nTop \d+ SELL candidates|\Z)",
        text, flags=re.S)
    sell_m = re.search(
        r"Top \d+ SELL candidates[^:]*:\s*\n-+\n(.*?)(?=\n—|\n\u2014|\Z)",
        text, flags=re.S)

    buy_text  = buy_m.group(1)  if buy_m  else ""
    sell_text = sell_m.group(1) if sell_m else ""

    buys  = [r for r in (parse_block(b) for b in split_blocks(buy_text))  if r]
    sells = [r for r in (parse_block(b) for b in split_blocks(sell_text)) if r]

    # ── fallback: scan whole file by bias if section parse is incomplete ─────
    if not buys and not sells:
        all_stocks = [r for r in (parse_block(b) for b in split_blocks(text)) if r]
        buys  = [s for s in all_stocks if not s["is_sell"]]
        sells = [s for s in all_stocks if s["is_sell"]]

    return {
        "generated":  gen_m.group(1).strip()  if gen_m  else "",
        "pov_hits":   int(hits_m.group(1))    if hits_m else 0,
        "buy_count":  int(rec_m.group(1))     if rec_m  else len(buys),
        "sell_count": int(rec_m.group(2))     if rec_m  else len(sells),
        "buys":       buys,
        "sells":      sells,
        "debug": {
            "buy_section_found":  buy_m  is not None,
            "sell_section_found": sell_m is not None,
            "buy_bullets_found":  len(buys),
            "sell_bullets_found": len(sells),
            "total_bullets":      len(re.findall(r"^\s*•", text, re.M)),
        },
    }


# ── load ─────────────────────────────────────────────────────────────────────
if not SUMMARY_PATH.exists():
    st.error(f"File not found:\n`{SUMMARY_PATH}`\n\nPut `stocks_in_trend_summary.txt` next to this script.")
    st.stop()

# Top bar: title + reload button
col_h, col_b = st.columns([6, 1])
with col_b:
    st.write("")
    if st.button("🔄 Reload", use_container_width=True):
        st.rerun()

text = SUMMARY_PATH.read_text(encoding="utf-8")
data = parse_file(text)

with col_h:
    st.markdown("# 📈 Stocks in Trend")
    st.caption(f"NSE bhavcopy · {data['generated'] or 'date unknown'} · Pure-on-Volume screen")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total BUY",  data["buy_count"])
c2.metric("Total SELL", data["sell_count"])
c3.metric("PoV hits",   data["pov_hits"])
c4.metric("Showing",    f"{len(data['buys'])} BUY · {len(data['sells'])} SELL")

st.warning("**Disclaimer:** Educational/analysis only. Not investment advice. "
           "Consult a SEBI-registered advisor. Trade at your own risk.", icon="⚠️")

# ── debug expander ─────────────────────────────────────────────────────────--
with st.expander("🔍 Debug — open if count is wrong"):
    d = data["debug"]
    st.json(d)
    if not d["buy_section_found"] or not d["sell_section_found"]:
        # Show first 300 chars so user can see what the file looks like
        st.warning("Section not found! First 400 chars of file:")
        st.code(text[:400])


# ── card renderer ─────────────────────────────────────────────────────────--
def render_signals(items: list[str], kind: str) -> None:
    if not items:
        return
    css   = "pro-li"  if kind == "pro" else "con-li"
    head  = "gh-pro"  if kind == "pro" else "gh-con"
    label = "Pros"    if kind == "pro" else "Cons"
    st.markdown(f'<div class="{head}">{label}</div>', unsafe_allow_html=True)
    st.markdown("".join(f'<div class="{css}">{i}</div>' for i in items),
                unsafe_allow_html=True)


def render_card(s: dict) -> None:
    pct     = s["change_pct"]
    pct_str = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
    pct_css = "pct-up" if pct > 0 else ("pct-down" if pct < 0 else "pct-flat")

    verdict  = s["verdict"] or s["bias"].replace("_", " ")
    vcss     = VERDICT_CSS.get(verdict.upper().strip(), "v-de")
    net      = s["net"]
    net_css  = "net-pos" if net > 0 else ("net-neg" if net < 0 else "net-zero")
    net_str  = f"+{net}" if net > 0 else str(net)

    with st.container(border=True):
        st.markdown(f"""
        <div class="card-header">
          <div>
            <div class="stock-symbol">{s["symbol"]}</div>
            <div class="stock-name">{s["name"]}</div>
          </div>
          <div class="price-block">
            <div class="price-label">Close</div>
            <div class="price-value">₹{s["price"]:,.2f}</div>
            <span class="{pct_css}">{pct_str}</span>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(
            f'<span class="verdict-badge {vcss}">{verdict}</span>'
            f'<span class="meta-pill">bias {s["bias"]}</span>'
            f'<span class="meta-pill">net <span class="{net_css}">{net_str}</span></span>',
            unsafe_allow_html=True)

        render_signals(s["signal_pros"], "pro")
        render_signals(s["signal_cons"], "con")

        if s["fundamentals"]:
            st.markdown(f'<div class="fund-row">{s["fundamentals"]}</div>',
                        unsafe_allow_html=True)

        if s["screener_pros"] or s["screener_cons"]:
            with st.expander("screener.in pros & cons"):
                render_signals(s["screener_pros"], "pro")
                render_signals(s["screener_cons"], "con")

        if s["url"]:
            st.markdown(f"[screener.in/{s['symbol']} ↗]({s['url']})")


# ── tabs ─────────────────────────────────────────────────────────────────────
buy_tab, sell_tab, raw_tab = st.tabs([
    f"💚  BUY  ({len(data['buys'])})",
    f"❤️  SELL  ({len(data['sells'])})",
    "📄  Raw file",
])

with buy_tab:
    if not data["buys"]:
        st.info("No BUY stocks found — open the 🔍 Debug panel above for details.")
    else:
        cols = st.columns(2)
        for i, s in enumerate(data["buys"]):
            with cols[i % 2]:
                render_card(s)

with sell_tab:
    if not data["sells"]:
        st.info("No SELL stocks found — open the 🔍 Debug panel above for details.")
    else:
        cols = st.columns(2)
        for i, s in enumerate(data["sells"]):
            with cols[i % 2]:
                render_card(s)

with raw_tab:
    st.caption(f"`{SUMMARY_PATH}` · {len(text):,} chars · {text.count(chr(10)):,} lines")
    st.code(text, language="text")
    st.download_button("⬇ Download txt", data=text,
                       file_name="stocks_in_trend_summary.txt", mime="text/plain")

# ── footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption("BUY/SELL based on *Pure_on_Volume* screen (HVQ/HVY/HVE breakouts + liquidity gate). "
           "Signal pros/cons from price-volume panel. Fundamentals from screener.in.")
