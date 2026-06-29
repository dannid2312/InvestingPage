import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ------------------------------------------------------------
# App config
# ------------------------------------------------------------
st.set_page_config(
    page_title="Market Watchlist Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

WATCHLIST_FILE = Path("watchlists.json")
DEFAULT_WATCHLISTS = {
    "AI Leaders": ["NVDA", "MSFT", "AMD"],
    "Mega Cap Tech": ["AAPL", "GOOGL", "AMZN"],
    "ASX Watchlist": ["BHP.AX", "CBA.AX", "WES.AX"],
}

PLOT_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "showTips": False,
    "staticPlot": True,
    "responsive": True,
}

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 48%, #eff6ff 100%);
            color: #0f172a;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1320px;
        }
        .hero-card {
            padding: 2rem;
            border: 1px solid #dbe3ef;
            border-radius: 1.5rem;
            background: #ffffff;
            box-shadow: 0 18px 60px rgba(15, 23, 42, 0.08);
        }
        .eyebrow {
            color: #2563eb;
            font-weight: 800;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            font-size: 0.78rem;
            margin-bottom: 0.75rem;
        }
        .hero-title {
            color: #0f172a;
            font-size: clamp(2rem, 5vw, 2.7rem);
            line-height: 1.05;
            font-weight: 850;
            margin: 0 0 0.9rem 0;
        }
        .hero-subtitle {
            color: #475569;
            max-width: 950px;
            font-size: clamp(0.98rem, 2.4vw, 1.05rem);
            line-height: 1.7;
            margin: 0;
        }
        .section-label {
            color: #0f172a;
            font-weight: 800;
            font-size: 1.08rem;
            margin-top: 0.25rem;
            margin-bottom: 0.15rem;
        }
        .section-help {
            color: #64748b;
            font-size: 0.92rem;
            margin-bottom: 0.75rem;
        }
        .stock-title {
            color: #0f172a;
            font-weight: 850;
            font-size: 1.15rem;
            margin-bottom: 0.1rem;
        }
        .stock-subtitle {
            color: #64748b;
            font-size: 0.86rem;
            margin-bottom: 0.6rem;
        }
        h1, h2, h3, h4, h5, h6, p, label, span, div {
            color: #0f172a;
        }
        .stCaption, [data-testid="stCaptionContainer"] {
            color: #64748b !important;
        }
        .stAlert {
            border-radius: 1rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #dbe3ef !important;
            background: #ffffff;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }
        div[data-testid="stExpander"] {
            border: 1px solid #dbe3ef;
            border-radius: 1.15rem;
            background: #ffffff;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.055);
        }
        div.stButton > button {
            width: 100%;
            border-radius: 0.85rem;
            min-height: 2.65rem;
            font-weight: 700;
        }
        .element-container:has(.js-plotly-plot) {
            overflow-x: hidden;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.85rem;
                padding-right: 0.85rem;
                padding-top: 0.9rem;
            }
            .hero-card {
                padding: 1.25rem;
                border-radius: 1.1rem;
            }
            div[data-testid="stExpander"] {
                border-radius: 1rem;
            }
            div[data-testid="stVerticalBlock"] {
                gap: 0.55rem;
            }
            div.stButton > button {
                min-height: 2.9rem;
                font-size: 0.95rem;
            }
            .stock-title {
                font-size: 1.05rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)



# ------------------------------------------------------------
# Extra responsive chart styling
# ------------------------------------------------------------
st.markdown(
    """
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            overflow-x: hidden !important;
        }
        div[data-testid="stPlotlyChart"],
        div[data-testid="stPlotlyChart"] > div,
        .js-plotly-plot,
        .plot-container,
        .svg-container {
            width: 100% !important;
            max-width: 100% !important;
            overflow: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            overflow: hidden !important;
        }
        div.stButton > button {
            width: 100%;
            border-radius: 0.85rem;
            min-height: 2.7rem;
            font-weight: 750;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.7rem !important;
                padding-right: 0.7rem !important;
                max-width: 100vw !important;
            }
            .hero-card {
                padding: 1.05rem !important;
                border-radius: 1rem !important;
            }
            .hero-title {
                font-size: 1.85rem !important;
            }
            .hero-subtitle {
                font-size: 0.95rem !important;
                line-height: 1.5 !important;
            }
            div.stButton > button {
                min-height: 2.9rem;
                font-size: 0.95rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Persistence helpers
# ------------------------------------------------------------
def load_watchlists() -> dict[str, list[str]]:
    if WATCHLIST_FILE.exists():
        try:
            data = json.loads(WATCHLIST_FILE.read_text())
            if isinstance(data, dict):
                return {str(name): list(symbols) for name, symbols in data.items()}
        except json.JSONDecodeError:
            pass
    return DEFAULT_WATCHLISTS.copy()


def save_watchlists(watchlists: dict[str, list[str]]) -> None:
    WATCHLIST_FILE.write_text(json.dumps(watchlists, indent=2))


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().replace(" ", "").upper()


def move_symbol(active_watchlist: str, symbol: str, direction: int) -> None:
    symbols = st.session_state.watchlists.get(active_watchlist, [])
    if symbol not in symbols:
        return
    current_index = symbols.index(symbol)
    new_index = current_index + direction
    if new_index < 0 or new_index >= len(symbols):
        return
    symbols[current_index], symbols[new_index] = symbols[new_index], symbols[current_index]
    st.session_state.watchlists[active_watchlist] = symbols
    save_watchlists(st.session_state.watchlists)


# ------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_history(symbol: str, interval: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="max", interval=interval)
    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
    date_col = "date" if "date" in df.columns else "datetime"
    df[date_col] = pd.to_datetime(df[date_col]).dt.tz_localize(None)
    df = df.rename(columns={date_col: "date"})
    required = ["date", "open", "high", "low", "close", "volume"]
    return df[required].dropna().sort_values("date").reset_index(drop=True)


def filter_display_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    if df.empty:
        return df
    latest_date = df["date"].max()
    offsets = {
        "1mo": pd.DateOffset(months=1),
        "3mo": pd.DateOffset(months=3),
        "6mo": pd.DateOffset(months=6),
        "1y": pd.DateOffset(years=1),
        "2y": pd.DateOffset(years=2),
        "5y": pd.DateOffset(years=5),
        "max": None,
    }
    if period == "max" or offsets.get(period) is None:
        return df.copy()
    start_date = latest_date - offsets[period]
    filtered = df[df["date"] >= start_date].copy()
    return filtered if not filtered.empty else df.tail(1).copy()




def reduce_points_for_mobile(df: pd.DataFrame, max_points: int) -> pd.DataFrame:
    """Keep phone charts readable by limiting visible index candles after indicator calculation."""
    if max_points <= 0 or len(df) <= max_points:
        return df
    return df.tail(max_points).copy()




def add_display_index(df: pd.DataFrame) -> pd.DataFrame:
    """Add a simple 1..N index for the chart x-axis instead of date labels."""
    indexed = df.copy().reset_index(drop=True)
    indexed["display_index"] = indexed.index + 1
    return indexed


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def add_sma_trace(fig: go.Figure, full_df: pd.DataFrame, display_df: pd.DataFrame, display_start: pd.Timestamp, period: int, color: str) -> None:
    if len(full_df) < period:
        return
    sma = full_df["close"].rolling(period).mean()
    indicator_df = pd.DataFrame({"date": full_df["date"], "sma": sma})
    indicator_df = indicator_df[indicator_df["date"] >= display_start].dropna()
    indicator_df = indicator_df.merge(display_df[["date", "display_index"]], on="date", how="inner")
    if indicator_df.empty:
        return
    fig.add_trace(
        go.Scatter(
            x=indicator_df["display_index"],
            y=indicator_df["sma"],
            mode="lines",
            name=f"SMA {period}",
            showlegend=False,
            line=dict(color=color, width=2.2),
        )
    )


def add_bollinger_bands(fig: go.Figure, full_df: pd.DataFrame, display_df: pd.DataFrame, display_start: pd.Timestamp, period: int = 20, std_dev: float = 2.0) -> None:
    if len(full_df) < period:
        return
    middle = full_df["close"].rolling(period).mean()
    std = full_df["close"].rolling(period).std()
    band_df = pd.DataFrame(
        {
            "date": full_df["date"],
            "upper": middle + std_dev * std,
            "lower": middle - std_dev * std,
        }
    )
    band_df = band_df[band_df["date"] >= display_start].dropna()
    band_df = band_df.merge(display_df[["date", "display_index"]], on="date", how="inner")
    if band_df.empty:
        return
    fig.add_trace(
        go.Scatter(
            x=band_df["display_index"],
            y=band_df["upper"],
            mode="lines",
            name="BB Upper",
            showlegend=False,
            line=dict(color="#9333ea", width=1.6, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=band_df["display_index"],
            y=band_df["lower"],
            mode="lines",
            name="BB Lower",
            showlegend=False,
            line=dict(color="#9333ea", width=1.6, dash="dot"),
            fill="tonexty",
            fillcolor="rgba(147, 51, 234, 0.08)",
        )
    )


def create_candlestick_chart(
    symbol: str,
    full_df: pd.DataFrame,
    display_df: pd.DataFrame,
    indicator_settings: dict[str, bool],
    show_volume: bool,
    show_rsi: bool,
    chart_ratio: float = 9 / 16,
) -> go.Figure:
    """Create a compact, mobile-friendly chart with no legend/title/x-axis labels.

    Streamlit controls the responsive width. The chart height is derived from the
    selected ratio so the chart scales more naturally across phone/tablet/desktop.
    """
    display_start = display_df["date"].min()
    display_df = add_display_index(display_df)

    # Ratio-based height. Streamlit does not expose the actual client width to Python,
    # so this uses practical width estimates plus bounds to keep the chart usable.
    base_width = 620
    chart_height = int(base_width * chart_ratio)
    chart_height = max(300, min(620, chart_height))
    if show_rsi:
        chart_height += 85

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=display_df["display_index"],
            open=display_df["open"],
            high=display_df["high"],
            low=display_df["low"],
            close=display_df["close"],
            name="",
            showlegend=False,
            increasing_line_color="#059669",
            decreasing_line_color="#dc2626",
            increasing_fillcolor="#10b981",
            decreasing_fillcolor="#ef4444",
            hoverinfo="skip",
        )
    )

    if indicator_settings["SMA20"]:
        add_sma_trace(fig, full_df, display_df, display_start, 20, "#2563eb")
    if indicator_settings["SMA50"]:
        add_sma_trace(fig, full_df, display_df, display_start, 50, "#f97316")
    if indicator_settings["SMA100"]:
        add_sma_trace(fig, full_df, display_df, display_start, 100, "#0891b2")
    if indicator_settings["SMA200"]:
        add_sma_trace(fig, full_df, display_df, display_start, 200, "#475569")
    if indicator_settings["Bollinger Bands"]:
        add_bollinger_bands(fig, full_df, display_df, display_start)

    if show_volume:
        colors = ["#10b981" if row.close >= row.open else "#ef4444" for row in display_df.itertuples()]
        fig.add_trace(
            go.Bar(
                x=display_df["display_index"],
                y=display_df["volume"],
                name="",
                showlegend=False,
                marker_color=colors,
                opacity=0.22,
                yaxis="y2",
                hoverinfo="skip",
            )
        )

    if show_rsi and len(full_df) >= 14:
        rsi_df = pd.DataFrame({"date": full_df["date"], "rsi": calculate_rsi(full_df["close"])})
        rsi_df = rsi_df[rsi_df["date"] >= display_start].dropna()
        rsi_df = rsi_df.merge(display_df[["date", "display_index"]], on="date", how="inner")
        if not rsi_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=rsi_df["display_index"],
                    y=rsi_df["rsi"],
                    mode="lines",
                    name="",
                    showlegend=False,
                    line=dict(color="#7c3aed", width=2.0),
                    yaxis="y3",
                    hoverinfo="skip",
                )
            )

    price_domain = [0.22, 1.0] if not show_rsi else [0.42, 1.0]

    fig.update_layout(
        title_text="",
        template="plotly_white",
        autosize=True,
        height=chart_height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8fafc",
        font=dict(color="#0f172a", family="Inter, Arial, sans-serif", size=9),
        dragmode=False,
        hovermode=False,
        showlegend=False,
        xaxis=dict(
            title_text="",
            rangeslider=dict(visible=False),
            fixedrange=True,
            showticklabels=False,
            ticks="",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title_text="",
            fixedrange=True,
            side="right",
            tickformat=".2f",
            nticks=5,
            tickfont=dict(size=9),
            automargin=True,
            showgrid=True,
            gridcolor="#e2e8f0",
            zeroline=False,
            domain=price_domain,
        ),
        yaxis2=dict(
            title_text="",
            fixedrange=True,
            domain=[0.0, 0.15],
            visible=show_volume,
            showticklabels=False,
            ticks="",
            showgrid=False,
            zeroline=False,
        ),
    )

    if show_rsi:
        fig.update_layout(
            yaxis=dict(
                title_text="",
                domain=[0.42, 1.0],
                side="right",
                fixedrange=True,
                automargin=True,
                showgrid=True,
                gridcolor="#e2e8f0",
                tickformat=".2f",
                nticks=5,
                tickfont=dict(size=9),
            ),
            yaxis2=dict(
                title_text="",
                domain=[0.22, 0.34],
                visible=show_volume,
                showticklabels=False,
                ticks="",
                fixedrange=True,
                showgrid=False,
            ),
            yaxis3=dict(
                title_text="",
                domain=[0.0, 0.16],
                range=[0, 100],
                fixedrange=True,
                side="right",
                nticks=3,
                showgrid=True,
                gridcolor="#e2e8f0",
                zeroline=False,
                automargin=True,
                tickfont=dict(size=9),
            ),
        )
        fig.add_hline(y=70, line_dash="dot", line_color="#dc2626", opacity=0.55, yref="y3")
        fig.add_hline(y=30, line_dash="dot", line_color="#059669", opacity=0.55, yref="y3")

    # Final hard override to prevent Plotly from displaying any legend/title.
    fig.update_layout(showlegend=False, title_text="")
    for trace in fig.data:
        trace.showlegend = False
        trace.name = ""

    return fig


def stock_price_summary(display_df: pd.DataFrame) -> tuple[str, str]:
    latest = display_df.iloc[-1]
    previous = display_df.iloc[-2] if len(display_df) > 1 else latest
    change_pct = ((latest["close"] - previous["close"]) / previous["close"]) * 100 if previous["close"] else 0
    return f"${latest['close']:.2f}", f"{change_pct:+.2f}%"


# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------
if "watchlists" not in st.session_state:
    st.session_state.watchlists = load_watchlists()

if "active_watchlist" not in st.session_state:
    st.session_state.active_watchlist = next(iter(st.session_state.watchlists.keys()))

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown(
    """
    <div class="hero-card">
        <div class="eyebrow">Market intelligence dashboard</div>
        <h1 class="hero-title">Professional Stock Watchlist Monitor</h1>
        <p class="hero-subtitle">
            Build watchlists, reorder stocks, and review fixed-position candlestick charts with long-horizon indicators calculated from full historical data.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------
# Main-page controls: mobile-friendly expanders
# ------------------------------------------------------------
watchlist_names = list(st.session_state.watchlists.keys())
if st.session_state.active_watchlist not in watchlist_names and watchlist_names:
    st.session_state.active_watchlist = watchlist_names[0]

with st.expander("Watchlist management", expanded=True):
    st.markdown('<div class="section-label">Select active watchlist</div>', unsafe_allow_html=True)
    selected = st.selectbox(
        "Active watchlist",
        watchlist_names,
        index=watchlist_names.index(st.session_state.active_watchlist),
        label_visibility="collapsed",
    )
    st.session_state.active_watchlist = selected

    st.markdown('<div class="section-label">Add stock ticker</div>', unsafe_allow_html=True)
    with st.form("add_symbol_form", clear_on_submit=True):
        symbol_input = st.text_input(
            "Ticker symbol",
            placeholder="AAPL, TSLA, BHP.AX, CBA.AX, BTC-USD",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Add stock")

    if submitted:
        active = st.session_state.active_watchlist
        symbols = st.session_state.watchlists.get(active, [])
        symbol = normalize_symbol(symbol_input)
        if not symbol:
            st.warning("Please enter a ticker symbol.")
        elif symbol in symbols:
            st.info(f"{symbol} is already in {active}.")
        else:
            st.session_state.watchlists[active].append(symbol)
            save_watchlists(st.session_state.watchlists)
            st.rerun()

    with st.expander("Create, rename, or delete watchlists", expanded=False):
        st.markdown('<div class="section-help">These actions are saved to watchlists.json.</div>', unsafe_allow_html=True)
        new_watchlist = st.text_input("New watchlist name", placeholder="e.g. Dividend Picks")
        if st.button("＋ Create watchlist"):
            name = new_watchlist.strip()
            if not name:
                st.warning("Please enter a watchlist name.")
            elif name in st.session_state.watchlists:
                st.warning("A watchlist with this name already exists.")
            else:
                st.session_state.watchlists[name] = []
                st.session_state.active_watchlist = name
                save_watchlists(st.session_state.watchlists)
                st.rerun()

        rename_value = st.text_input("Rename selected watchlist", value=st.session_state.active_watchlist)
        if st.button("Rename selected watchlist"):
            old_name = st.session_state.active_watchlist
            new_name = rename_value.strip()
            if not new_name:
                st.warning("Name cannot be empty.")
            elif new_name != old_name and new_name in st.session_state.watchlists:
                st.warning("That watchlist name already exists.")
            else:
                st.session_state.watchlists[new_name] = st.session_state.watchlists.pop(old_name)
                st.session_state.active_watchlist = new_name
                save_watchlists(st.session_state.watchlists)
                st.rerun()

        if st.button("Delete selected watchlist", disabled=len(st.session_state.watchlists) <= 1):
            st.session_state.watchlists.pop(st.session_state.active_watchlist, None)
            st.session_state.active_watchlist = next(iter(st.session_state.watchlists.keys()))
            save_watchlists(st.session_state.watchlists)
            st.rerun()

with st.expander("Chart settings and indicators", expanded=True):
    st.markdown('<div class="section-help">Indicators use full historical data; visible period only controls what part of the chart is displayed.</div>', unsafe_allow_html=True)
    mobile_mode = st.toggle("Mobile optimised chart", value=True)
    period = st.selectbox("Visible period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=1)
    interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)
    chart_ratio_name = st.selectbox("Chart ratio", ["Compact 16:9", "Balanced 4:3", "Tall mobile 1:1"], index=0)
    max_visible_points = st.select_slider(
        "Max visible candles",
        options=[20, 30, 45, 60, 75, 90, 120, 180],
        value=60,
    )

    st.markdown('<div class="section-label">Indicators</div>', unsafe_allow_html=True)
    show_sma20 = st.toggle("SMA 20", value=True)
    show_sma50 = st.toggle("SMA 50", value=False)
    show_sma100 = st.toggle("SMA 100", value=False)
    show_sma200 = st.toggle("SMA 200", value=False)
    show_bollinger = st.toggle("Bollinger Bands", value=False)
    show_volume = st.toggle("Volume", value=True)
    show_rsi = st.toggle("RSI 14", value=False)

    if st.button("Refresh market data"):
        fetch_stock_history.clear()
        st.rerun()

chart_ratio = {"Compact 16:9": 9/16, "Balanced 4:3": 3/4, "Tall mobile 1:1": 1.0}[chart_ratio_name]

indicator_settings = {
    "SMA20": show_sma20,
    "SMA50": show_sma50,
    "SMA100": show_sma100,
    "SMA200": show_sma200,
    "Bollinger Bands": show_bollinger,
}

st.divider()

# ------------------------------------------------------------
# Watchlist charts
# ------------------------------------------------------------
active = st.session_state.active_watchlist
symbols = st.session_state.watchlists.get(active, [])

st.subheader(active)
st.caption(f"{len(symbols)} stock(s) in this watchlist")

if not symbols:
    st.info("This watchlist is empty. Add a ticker above to show its candlestick chart.")
else:
    for index, symbol in enumerate(symbols):
        with st.container(border=True):
            st.markdown(f'<div class="stock-title">{index + 1}. {symbol}</div>', unsafe_allow_html=True)
            st.markdown('<div class="stock-subtitle">Use the management section below to reorder or remove this stock.</div>', unsafe_allow_html=True)

            with st.expander(f"Manage {symbol}", expanded=False):
                if st.button("↑ Move up", key=f"up-{active}-{symbol}", disabled=index == 0):
                    move_symbol(active, symbol, -1)
                    st.rerun()
                if st.button("↓ Move down", key=f"down-{active}-{symbol}", disabled=index == len(symbols) - 1):
                    move_symbol(active, symbol, 1)
                    st.rerun()
                if st.button("Remove from watchlist", key=f"remove-{active}-{symbol}"):
                    st.session_state.watchlists[active] = [item for item in symbols if item != symbol]
                    save_watchlists(st.session_state.watchlists)
                    st.rerun()

            with st.spinner(f"Loading {symbol} from yfinance..."):
                full_df = fetch_stock_history(symbol, interval)

            if full_df.empty:
                st.error(f"No data found for {symbol}. Check the ticker symbol or interval.")
                continue

            display_df = filter_display_period(full_df, period)
            display_df = reduce_points_for_mobile(display_df, max_visible_points)

            if len(full_df) < 200 and show_sma200:
                st.caption(f"{symbol}: SMA 200 needs at least 200 data points. Available: {len(full_df)}.")

            fig = create_candlestick_chart(
                symbol=symbol,
                full_df=full_df,
                display_df=display_df,
                indicator_settings=indicator_settings,
                show_volume=show_volume,
                show_rsi=show_rsi,
                chart_ratio=chart_ratio,
            )
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

st.caption(
    "Data is provided through yfinance/Yahoo Finance. This dashboard is for educational and informational use only, not financial advice."
)
