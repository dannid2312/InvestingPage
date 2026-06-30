import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Market Watchlist Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

WATCHLIST_FILE = Path("watchlists.json")
DEFAULT_WATCHLISTS = {
    "AI Leaders": ["NVDA", "MSFT", "AMD"],
    "Mega Cap Tech": ["AAPL", "GOOGL", "AMZN"],
    "ASX Watchlist": ["BHP.AX", "CBA.AX", "WES.AX"],
}
PLOT_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False, "staticPlot": True, "responsive": True}

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden !important; }
.stApp { background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 48%, #eff6ff 100%); color: #0f172a; }
.block-container { padding-top: 1rem; padding-bottom: 3rem; max-width: 1120px; }
section[data-testid="stSidebar"] { background:#ffffff; border-right:1px solid #dbe3ef; }
section[data-testid="stSidebar"] * { color:#0f172a; }
.hero-card { padding: 1.55rem; border: 1px solid #dbe3ef; border-radius: 1.3rem; background: #fff; box-shadow: 0 18px 60px rgba(15,23,42,.08); }
.eyebrow { color: #2563eb; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; font-size: .76rem; margin-bottom: .65rem; }
.hero-title { color:#0f172a; font-size: clamp(1.75rem,5vw,2.65rem); line-height:1.08; font-weight:850; margin:0 0 .75rem 0; }
.hero-subtitle { color:#475569; max-width:920px; font-size: clamp(.95rem,2.4vw,1.05rem); line-height:1.6; margin:0; }
.section-label { color:#0f172a; font-weight:800; font-size:1.02rem; margin-top:.25rem; margin-bottom:.15rem; }
.stock-head { display:flex; align-items:flex-start; justify-content:space-between; gap:.75rem; flex-wrap:wrap; margin-bottom:.4rem; }
.stock-title { font-weight:850; font-size:clamp(1rem,3vw,1.18rem); }
.stock-sub { color:#64748b; font-size:.82rem; }
.price-pill { border:1px solid #dbe3ef; border-radius:999px; background:#f8fafc; padding:.36rem .62rem; color:#334155; font-size:.82rem; font-weight:750; white-space:nowrap; }
.indicator-row { color:#475569; font-size:.78rem; line-height:1.45; margin:.15rem 0 .45rem 0; }
h1,h2,h3,h4,h5,h6,p,label,span,div { color:#0f172a; }
.stCaption, [data-testid="stCaptionContainer"] { color:#64748b !important; }
div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"] { border-color:#dbe3ef !important; background:#fff; box-shadow:0 10px 30px rgba(15,23,42,.05); overflow:hidden !important; }
div.stButton > button { width:100%; border-radius:.85rem; min-height:2.7rem; font-weight:750; }
div[data-testid="stPlotlyChart"], div[data-testid="stPlotlyChart"] > div, .js-plotly-plot, .plot-container, .svg-container { width:100% !important; max-width:100% !important; overflow:hidden !important; }
@media (max-width:768px){ .block-container{padding-left:.65rem !important; padding-right:.65rem !important; max-width:100vw !important;} .hero-card{padding:1rem; border-radius:1rem;} .hero-title{font-size:1.8rem !important;} .hero-subtitle{font-size:.94rem !important; line-height:1.5 !important;} .price-pill{font-size:.76rem; padding:.32rem .5rem;} div.stButton > button{min-height:2.9rem; font-size:.95rem;} }
</style>
""", unsafe_allow_html=True)


def load_watchlists():
    if WATCHLIST_FILE.exists():
        try:
            data = json.loads(WATCHLIST_FILE.read_text())
            if isinstance(data, dict):
                return {str(k): list(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass
    return DEFAULT_WATCHLISTS.copy()


def save_watchlists(watchlists):
    WATCHLIST_FILE.write_text(json.dumps(watchlists, indent=2))


def normalize_symbol(symbol):
    return str(symbol).strip().replace(" ", "").upper()


def symbols_from_uploaded_csv(uploaded_file):
    """Extract ticker symbols from CSV.

    Supported layouts:
    - Preferred column names: symbol, ticker, tickers, stock, stocks, code
    - Otherwise, the first column is used
    """
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        return []
    if df.empty:
        return []
    preferred = ["symbol", "ticker", "tickers", "stock", "stocks", "code"]
    lowered = {str(col).strip().lower(): col for col in df.columns}
    selected = next((lowered[name] for name in preferred if name in lowered), df.columns[0])
    symbols = []
    for value in df[selected].dropna().tolist():
        symbol = normalize_symbol(value)
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def move_symbol(active_watchlist, symbol, direction):
    symbols = st.session_state.watchlists.get(active_watchlist, [])
    if symbol not in symbols:
        return
    i = symbols.index(symbol)
    j = i + direction
    if 0 <= j < len(symbols):
        symbols[i], symbols[j] = symbols[j], symbols[i]
        st.session_state.watchlists[active_watchlist] = symbols
        save_watchlists(st.session_state.watchlists)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_history(symbol, interval):
    df = yf.Ticker(symbol).history(period="max", interval=interval)
    if df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    date_col = "date" if "date" in df.columns else "datetime"
    df[date_col] = pd.to_datetime(df[date_col]).dt.tz_localize(None)
    df = df.rename(columns={date_col: "date"})
    return df[["date", "open", "high", "low", "close", "volume"]].dropna().sort_values("date").reset_index(drop=True)


def visible_candles(df, max_points):
    return df.tail(max_points).copy() if len(df) > max_points else df.copy()


def add_index(df):
    out = df.copy().reset_index(drop=True)
    out["display_index"] = out.index + 1
    return out


def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd(close, fast=12, slow=26, signal=9):
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def overlay_label(settings, show_volume, show_rsi, show_macd):
    items = [name.replace("SMA", "SMA ") for name, enabled in settings.items() if enabled]
    if show_volume:
        items.append("Volume")
    if show_rsi:
        items.append("RSI 14")
    if show_macd:
        items.append("MACD")
    return " · ".join(items) if items else "No overlays"


def add_sma(fig, full_df, display_df, start_date, period, color):
    if len(full_df) < period:
        return
    data = pd.DataFrame({"date": full_df["date"], "value": full_df["close"].rolling(period).mean()})
    data = data[data["date"] >= start_date].dropna().merge(display_df[["date", "display_index"]], on="date", how="inner")
    if not data.empty:
        fig.add_trace(go.Scatter(x=data["display_index"], y=data["value"], mode="lines", name="", showlegend=False, line=dict(color=color, width=2), hoverinfo="skip"))


def add_bbands(fig, full_df, display_df, start_date):
    if len(full_df) < 20:
        return
    mid = full_df["close"].rolling(20).mean()
    std = full_df["close"].rolling(20).std()
    data = pd.DataFrame({"date": full_df["date"], "upper": mid + 2 * std, "lower": mid - 2 * std})
    data = data[data["date"] >= start_date].dropna().merge(display_df[["date", "display_index"]], on="date", how="inner")
    if data.empty:
        return
    fig.add_trace(go.Scatter(x=data["display_index"], y=data["upper"], mode="lines", name="", showlegend=False, line=dict(color="#9333ea", width=1.2, dash="dot"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=data["display_index"], y=data["lower"], mode="lines", name="", showlegend=False, line=dict(color="#9333ea", width=1.2, dash="dot"), fill="tonexty", fillcolor="rgba(147,51,234,.08)", hoverinfo="skip"))


def make_chart(symbol, full_df, display_df, settings, show_volume, show_rsi, show_macd, price_height):
    start_date = display_df["date"].min()
    display_df = add_index(display_df)
    panel_heights = []
    if show_macd:
        panel_heights.append(("macd", 95))
    if show_rsi:
        panel_heights.append(("rsi", 85))
    if show_volume:
        panel_heights.append(("volume", 65))
    gap = 12
    total_height = int(price_height) + sum(h for _, h in panel_heights) + gap * len(panel_heights)
    domains = {}
    cursor = 0
    for panel, h in panel_heights:
        domains[panel] = [cursor / total_height, (cursor + h) / total_height]
        cursor += h + gap
    domains["price"] = [cursor / total_height, 1.0]

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=display_df["display_index"], open=display_df["open"], high=display_df["high"], low=display_df["low"], close=display_df["close"], name="", showlegend=False, increasing_line_color="#059669", decreasing_line_color="#dc2626", increasing_fillcolor="#10b981", decreasing_fillcolor="#ef4444", hoverinfo="skip"))
    if settings["SMA20"]: add_sma(fig, full_df, display_df, start_date, 20, "#2563eb")
    if settings["SMA50"]: add_sma(fig, full_df, display_df, start_date, 50, "#f97316")
    if settings["SMA100"]: add_sma(fig, full_df, display_df, start_date, 100, "#0891b2")
    if settings["SMA200"]: add_sma(fig, full_df, display_df, start_date, 200, "#475569")
    if settings["Bollinger Bands"]: add_bbands(fig, full_df, display_df, start_date)
    if show_volume:
        colors = ["#10b981" if row.close >= row.open else "#ef4444" for row in display_df.itertuples()]
        fig.add_trace(go.Bar(x=display_df["display_index"], y=display_df["volume"], name="", showlegend=False, marker_color=colors, opacity=.22, yaxis="y2", hoverinfo="skip"))
    if show_rsi and len(full_df) >= 14:
        rr = pd.DataFrame({"date": full_df["date"], "value": rsi(full_df["close"])})
        rr = rr[rr["date"] >= start_date].dropna().merge(display_df[["date", "display_index"]], on="date", how="inner")
        if not rr.empty:
            fig.add_trace(go.Scatter(x=rr["display_index"], y=rr["value"], mode="lines", name="", showlegend=False, line=dict(color="#7c3aed", width=2), yaxis="y3", hoverinfo="skip"))
    if show_macd and len(full_df) >= 35:
        macd_line, signal_line, histogram = macd(full_df["close"])
        mm = pd.DataFrame({"date": full_df["date"], "macd": macd_line, "signal": signal_line, "hist": histogram})
        mm = mm[mm["date"] >= start_date].dropna().merge(display_df[["date", "display_index"]], on="date", how="inner")
        if not mm.empty:
            hist_colors = ["#10b981" if value >= 0 else "#ef4444" for value in mm["hist"]]
            fig.add_trace(go.Bar(x=mm["display_index"], y=mm["hist"], name="", showlegend=False, marker_color=hist_colors, opacity=.35, yaxis="y4", hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=mm["display_index"], y=mm["macd"], mode="lines", name="", showlegend=False, line=dict(color="#2563eb", width=1.8), yaxis="y4", hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=mm["display_index"], y=mm["signal"], mode="lines", name="", showlegend=False, line=dict(color="#f97316", width=1.6), yaxis="y4", hoverinfo="skip"))

    axis_font = dict(size=10, family="Arial, sans-serif", color="#334155")
    price_min = float(display_df["low"].min())
    price_max = float(display_df["high"].max())
    price_pad = (price_max - price_min) * 0.04 if price_max > price_min else 1
    price_range = [price_min - price_pad, price_max + price_pad]
    volume_range = [0, float(display_df["volume"].max())] if show_volume else [0, 1]

    fig.update_layout(title_text="", template="plotly_white", autosize=True, height=total_height, margin=dict(l=44, r=44, t=0, b=0), paper_bgcolor="#fff", plot_bgcolor="#f8fafc", dragmode=False, hovermode=False, showlegend=False, font=dict(size=10, family="Arial, sans-serif", color="#0f172a"), xaxis=dict(title_text="", rangeslider=dict(visible=False), fixedrange=True, showticklabels=False, ticks="", showgrid=False, zeroline=False), yaxis=dict(title_text="", fixedrange=True, side="right", range=price_range, tickformat=".2f", nticks=5, automargin=True, tickfont=axis_font, showgrid=True, gridcolor="#e2e8f0", zeroline=False, domain=domains["price"]), yaxis2=dict(title_text="", fixedrange=True, side="right", range=volume_range, domain=domains.get("volume", [0, 0]), visible=show_volume, showticklabels=show_volume, tickfont=axis_font, nticks=2, ticks="", automargin=True, showgrid=False, zeroline=False), yaxis5=dict(title_text="", overlaying="y", side="left", fixedrange=True, range=price_range, showticklabels=True, tickformat=".2f", nticks=5, ticks="", automargin=True, tickfont=axis_font, showgrid=False, zeroline=False), yaxis6=dict(title_text="", overlaying="y2", side="left", fixedrange=True, range=volume_range, visible=show_volume, showticklabels=show_volume, nticks=2, ticks="", automargin=True, tickfont=axis_font, showgrid=False, zeroline=False))
    fig.add_trace(go.Scatter(x=display_df["display_index"], y=display_df["close"], yaxis="y5", mode="lines", line=dict(width=0), opacity=0, showlegend=False, hoverinfo="skip", name=""))
    if show_volume:
        fig.add_trace(go.Scatter(x=display_df["display_index"], y=display_df["volume"], yaxis="y6", mode="lines", line=dict(width=0), opacity=0, showlegend=False, hoverinfo="skip", name=""))
    if show_rsi:
        fig.update_layout(yaxis3=dict(title_text="", domain=domains.get("rsi", [0, 0]), range=[0, 100], fixedrange=True, side="right", nticks=3, showticklabels=True, showgrid=True, gridcolor="#e2e8f0", zeroline=False, automargin=True, tickfont=axis_font), yaxis7=dict(title_text="", overlaying="y3", side="left", range=[0, 100], fixedrange=True, nticks=3, showticklabels=True, ticks="", automargin=True, tickfont=axis_font, showgrid=False, zeroline=False))
        fig.add_trace(go.Scatter(x=display_df["display_index"], y=[50] * len(display_df), yaxis="y7", mode="lines", line=dict(width=0), opacity=0, showlegend=False, hoverinfo="skip", name=""))
        fig.add_hline(y=70, line_dash="dot", line_color="#dc2626", opacity=.55, yref="y3")
        fig.add_hline(y=30, line_dash="dot", line_color="#059669", opacity=.55, yref="y3")
    if show_macd:
        macd_range = None
        if 'mm' in locals() and not mm.empty:
            max_abs = float(max(abs(mm["macd"]).max(), abs(mm["signal"]).max(), abs(mm["hist"]).max()))
            macd_range = [-max(max_abs, 0.01) * 1.15, max(max_abs, 0.01) * 1.15]
        fig.update_layout(yaxis4=dict(title_text="", domain=domains.get("macd", [0, 0]), range=macd_range, fixedrange=True, side="right", nticks=3, showticklabels=True, showgrid=True, gridcolor="#e2e8f0", zeroline=True, zerolinecolor="#94a3b8", automargin=True, tickfont=axis_font), yaxis8=dict(title_text="", overlaying="y4", side="left", range=macd_range, fixedrange=True, nticks=3, showticklabels=True, ticks="", automargin=True, tickfont=axis_font, showgrid=False, zeroline=False))
        if macd_range is not None:
            fig.add_trace(go.Scatter(x=display_df["display_index"], y=[0] * len(display_df), yaxis="y8", mode="lines", line=dict(width=0), opacity=0, showlegend=False, hoverinfo="skip", name=""))
    for trace in fig.data:
        trace.showlegend = False
        trace.name = ""
    fig.update_layout(showlegend=False, title_text="")
    return fig


def price_summary(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest
    pct = ((latest["close"] - previous["close"]) / previous["close"] * 100) if previous["close"] else 0
    return f"${latest['close']:.2f}", f"{pct:+.2f}%"


if "watchlists" not in st.session_state:
    st.session_state.watchlists = load_watchlists()
if "active_watchlist" not in st.session_state:
    st.session_state.active_watchlist = next(iter(st.session_state.watchlists.keys()))

st.markdown("""
<div class="hero-card">
  <div class="eyebrow">Market intelligence dashboard</div>
  <h1 class="hero-title">Professional Stock Watchlist Monitor</h1>
  <p class="hero-subtitle">Build watchlists, reorder stocks, and review compact candlestick charts designed for desktop, tablet, and mobile screens.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

names = list(st.session_state.watchlists.keys())
if st.session_state.active_watchlist not in names and names:
    st.session_state.active_watchlist = names[0]

with st.sidebar:
    st.header("Watchlist")
    st.caption("Create, select, rename, and manage your ticker lists.")
    st.markdown('<div class="section-label">Active watchlist</div>', unsafe_allow_html=True)
    st.session_state.active_watchlist = st.selectbox("Active watchlist", names, index=names.index(st.session_state.active_watchlist), label_visibility="collapsed")
    st.markdown('<div class="section-label">Add stock ticker</div>', unsafe_allow_html=True)
    with st.form("add_symbol_form", clear_on_submit=True):
        symbol_input = st.text_input("Ticker symbol", placeholder="AAPL, TSLA, BHP.AX, CBA.AX, BTC-USD", label_visibility="collapsed")
        submitted = st.form_submit_button("Add stock")
    if submitted:
        active = st.session_state.active_watchlist
        symbol = normalize_symbol(symbol_input)
        if not symbol:
            st.warning("Please enter a ticker symbol.")
        elif symbol in st.session_state.watchlists[active]:
            st.info(f"{symbol} is already in {active}.")
        else:
            st.session_state.watchlists[active].append(symbol)
            save_watchlists(st.session_state.watchlists)
            st.rerun()

    st.markdown('<div class="section-label">Create watchlist from CSV</div>', unsafe_allow_html=True)
    uploaded_csv = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed", help="Use a CSV with a symbol/ticker column, or put symbols in the first column.")
    csv_watchlist_name = st.text_input("CSV watchlist name", placeholder="e.g. My CSV Watchlist")
    if st.button("Create watchlist from CSV"):
        if uploaded_csv is None:
            st.warning("Please upload a CSV file first.")
        else:
            csv_symbols = symbols_from_uploaded_csv(uploaded_csv)
            if not csv_symbols:
                st.warning("No ticker symbols were found in the CSV.")
            else:
                default_name = Path(uploaded_csv.name).stem.replace("_", " ").replace("-", " ").title()
                base_name = csv_watchlist_name.strip() or default_name or "CSV Watchlist"
                name = base_name
                counter = 2
                while name in st.session_state.watchlists:
                    name = f"{base_name} {counter}"
                    counter += 1
                st.session_state.watchlists[name] = csv_symbols
                st.session_state.active_watchlist = name
                save_watchlists(st.session_state.watchlists)
                st.success(f"Created {name} with {len(csv_symbols)} symbol(s).")
                st.rerun()

    with st.expander("Create / rename / delete", expanded=False):
        new_name = st.text_input("New watchlist name", placeholder="e.g. Dividend Picks")
        if st.button("＋ Create watchlist"):
            name = new_name.strip()
            if not name:
                st.warning("Please enter a watchlist name.")
            elif name in st.session_state.watchlists:
                st.warning("A watchlist with this name already exists.")
            else:
                st.session_state.watchlists[name] = []
                st.session_state.active_watchlist = name
                save_watchlists(st.session_state.watchlists)
                st.rerun()
        rename_name = st.text_input("Rename selected watchlist", value=st.session_state.active_watchlist)
        if st.button("Rename selected watchlist"):
            old = st.session_state.active_watchlist
            new = rename_name.strip()
            if not new:
                st.warning("Name cannot be empty.")
            elif new != old and new in st.session_state.watchlists:
                st.warning("That watchlist name already exists.")
            else:
                st.session_state.watchlists[new] = st.session_state.watchlists.pop(old)
                st.session_state.active_watchlist = new
                save_watchlists(st.session_state.watchlists)
                st.rerun()
        if st.button("Delete selected watchlist", disabled=len(st.session_state.watchlists) <= 1):
            st.session_state.watchlists.pop(st.session_state.active_watchlist, None)
            st.session_state.active_watchlist = next(iter(st.session_state.watchlists.keys()))
            save_watchlists(st.session_state.watchlists)
            st.rerun()

    st.divider()
    st.header("Chart settings")
    st.caption("Visible candles control the displayed recent range; indicators still use full history.")
    interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)
    st.caption("Chart uses flexible width and a fixed 250 px main candlestick height.")
    price_height = 250
    max_points = st.select_slider("Visible recent candles", options=[20, 30, 45, 60, 75, 90, 120, 180], value=60)
    st.markdown('<div class="section-label">Indicators</div>', unsafe_allow_html=True)
    show_sma20 = st.toggle("SMA 20", value=True)
    show_sma50 = st.toggle("SMA 50", value=False)
    show_sma100 = st.toggle("SMA 100", value=False)
    show_sma200 = st.toggle("SMA 200", value=False)
    show_bbands = st.toggle("Bollinger Bands", value=False)
    show_volume = st.toggle("Volume", value=True)
    show_rsi = st.toggle("RSI 14", value=False)
    show_macd = st.toggle("MACD", value=False)
    if st.button("Refresh market data"):
        fetch_stock_history.clear()
        st.rerun()

settings = {"SMA20": show_sma20, "SMA50": show_sma50, "SMA100": show_sma100, "SMA200": show_sma200, "Bollinger Bands": show_bbands}

st.divider()
active = st.session_state.active_watchlist
symbols = st.session_state.watchlists.get(active, [])
st.subheader(active)
st.caption(f"{len(symbols)} stock(s) in this watchlist")

if not symbols:
    st.info("This watchlist is empty. Add a ticker above to show its candlestick chart.")
else:
    for i, symbol in enumerate(symbols):
        with st.container(border=True):
            with st.spinner(f"Loading {symbol} from yfinance..."):
                full_df = fetch_stock_history(symbol, interval)
            if full_df.empty:
                st.error(f"No data found for {symbol}. Check the ticker symbol or interval.")
                continue
            display_df = visible_candles(full_df, max_points)
            price, pct = price_summary(display_df)
            st.markdown(f"""
<div class="stock-head">
  <div><div class="stock-title">{i + 1}. {symbol}</div><div class="stock-sub">{len(display_df)} indexed candles · no x-axis labels</div></div>
  <div class="price-pill">{price} · {pct}</div>
</div>
""", unsafe_allow_html=True)
            st.markdown(f'<div class="indicator-row">{overlay_label(settings, show_volume, show_rsi, show_macd)}</div>', unsafe_allow_html=True)
            with st.expander(f"Manage {symbol}", expanded=False):
                if st.button("↑ Move up", key=f"up-{active}-{symbol}", disabled=i == 0):
                    move_symbol(active, symbol, -1)
                    st.rerun()
                if st.button("↓ Move down", key=f"down-{active}-{symbol}", disabled=i == len(symbols) - 1):
                    move_symbol(active, symbol, 1)
                    st.rerun()
                if st.button("Remove from watchlist", key=f"remove-{active}-{symbol}"):
                    st.session_state.watchlists[active] = [item for item in symbols if item != symbol]
                    save_watchlists(st.session_state.watchlists)
                    st.rerun()
            if len(full_df) < 200 and show_sma200:
                st.caption(f"{symbol}: SMA 200 needs at least 200 data points. Available: {len(full_df)}.")
            if len(full_df) < 35 and show_macd:
                st.caption(f"{symbol}: MACD needs at least 35 data points. Available: {len(full_df)}.")
            fig = make_chart(symbol, full_df, display_df, settings, show_volume, show_rsi, show_macd, price_height)
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

st.caption("Data is provided through yfinance/Yahoo Finance. This dashboard is for educational and informational use only, not financial advice.")
