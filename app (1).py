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
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1440px;
        }
        .hero-card {
            padding: 2.1rem;
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
            font-size: 2.7rem;
            line-height: 1.05;
            font-weight: 850;
            margin: 0 0 0.9rem 0;
        }
        .hero-subtitle {
            color: #475569;
            max-width: 950px;
            font-size: 1.05rem;
            line-height: 1.7;
            margin: 0;
        }
        .panel-title {
            color: #0f172a;
            font-weight: 800;
            font-size: 1.05rem;
            margin-bottom: 0.35rem;
        }
        .panel-subtitle {
            color: #64748b;
            font-size: 0.9rem;
            margin-bottom: 1rem;
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
    """Move a symbol up (-1) or down (+1) within the active watchlist."""
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
    """
    Fetch the full available history for the symbol.

    SMA lines are calculated from this full history first, then filtered to the
    visible chart range. This lets long indicators like SMA 100 and SMA 200
    appear even when the displayed chart period is only 1mo or 3mo.
    """
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


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def add_sma_trace(fig: go.Figure, full_df: pd.DataFrame, display_start: pd.Timestamp, period: int, color: str) -> None:
    if len(full_df) < period:
        return

    sma = full_df["close"].rolling(period).mean()
    indicator_df = pd.DataFrame({"date": full_df["date"], "sma": sma})
    indicator_df = indicator_df[indicator_df["date"] >= display_start].dropna()

    if indicator_df.empty:
        return

    fig.add_trace(
        go.Scatter(
            x=indicator_df["date"],
            y=indicator_df["sma"],
            mode="lines",
            name=f"SMA {period}",
            line=dict(color=color, width=2.2),
        )
    )


def add_bollinger_bands(fig: go.Figure, full_df: pd.DataFrame, display_start: pd.Timestamp, period: int = 20, std_dev: float = 2.0) -> None:
    if len(full_df) < period:
        return

    middle = full_df["close"].rolling(period).mean()
    std = full_df["close"].rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std

    band_df = pd.DataFrame(
        {
            "date": full_df["date"],
            "upper": upper,
            "lower": lower,
        }
    )
    band_df = band_df[band_df["date"] >= display_start].dropna()

    if band_df.empty:
        return

    fig.add_trace(
        go.Scatter(
            x=band_df["date"],
            y=band_df["upper"],
            mode="lines",
            name="BB Upper",
            line=dict(color="#9333ea", width=1.6, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=band_df["date"],
            y=band_df["lower"],
            mode="lines",
            name="BB Lower",
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
) -> go.Figure:
    fig = go.Figure()
    display_start = display_df["date"].min()

    fig.add_trace(
        go.Candlestick(
            x=display_df["date"],
            open=display_df["open"],
            high=display_df["high"],
            low=display_df["low"],
            close=display_df["close"],
            name=symbol,
            increasing_line_color="#059669",
            decreasing_line_color="#dc2626",
            increasing_fillcolor="#10b981",
            decreasing_fillcolor="#ef4444",
        )
    )

    # Indicators are calculated from full history, then shown only over the visible range.
    if indicator_settings["SMA20"]:
        add_sma_trace(fig, full_df, display_start, 20, "#2563eb")
    if indicator_settings["SMA50"]:
        add_sma_trace(fig, full_df, display_start, 50, "#f97316")
    if indicator_settings["SMA100"]:
        add_sma_trace(fig, full_df, display_start, 100, "#0891b2")
    if indicator_settings["SMA200"]:
        add_sma_trace(fig, full_df, display_start, 200, "#475569")
    if indicator_settings["Bollinger Bands"]:
        add_bollinger_bands(fig, full_df, display_start, period=20, std_dev=2.0)

    if show_volume:
        colors = ["#10b981" if row.close >= row.open else "#ef4444" for row in display_df.itertuples()]
        fig.add_trace(
            go.Bar(
                x=display_df["date"],
                y=display_df["volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.24,
                yaxis="y2",
            )
        )

    if show_rsi and len(full_df) >= 14:
        rsi_df = pd.DataFrame(
            {
                "date": full_df["date"],
                "rsi": calculate_rsi(full_df["close"]),
            }
        )
        rsi_df = rsi_df[rsi_df["date"] >= display_start].dropna()
        if not rsi_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=rsi_df["date"],
                    y=rsi_df["rsi"],
                    mode="lines",
                    name="RSI 14",
                    line=dict(color="#7c3aed", width=2.3),
                    yaxis="y3",
                )
            )

    latest = display_df.iloc[-1]
    previous = display_df.iloc[-2] if len(display_df) > 1 else latest
    change_pct = ((latest["close"] - previous["close"]) / previous["close"]) * 100 if previous["close"] else 0

    fig.update_layout(
        title=dict(
            text=f"{symbol} · ${latest['close']:.2f} · {change_pct:+.2f}%",
            font=dict(color="#0f172a", size=20),
            x=0.01,
        ),
        template="plotly_white",
        height=520 if show_rsi else 455,
        margin=dict(l=20, r=20, t=52, b=26),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8fafc",
        font=dict(color="#0f172a", family="Inter, Arial, sans-serif"),
        dragmode=False,
        hovermode="x unified",
        xaxis=dict(
            rangeslider=dict(visible=False),
            fixedrange=True,
            showgrid=True,
            gridcolor="#e2e8f0",
            linecolor="#cbd5e1",
            zeroline=False,
        ),
        yaxis=dict(
            title="Price",
            fixedrange=True,
            domain=[0.28 if show_rsi else 0.18, 1.0],
            showgrid=True,
            gridcolor="#e2e8f0",
            linecolor="#cbd5e1",
            zeroline=False,
        ),
        yaxis2=dict(
            title="Volume",
            fixedrange=True,
            domain=[0.0, 0.16],
            showgrid=False,
            visible=show_volume,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#334155", size=11),
        ),
    )

    if show_rsi:
        fig.update_layout(
            yaxis=dict(domain=[0.42, 1.0], fixedrange=True, showgrid=True, gridcolor="#e2e8f0"),
            yaxis2=dict(domain=[0.22, 0.34], fixedrange=True, visible=show_volume, showgrid=False),
            yaxis3=dict(
                title="RSI",
                domain=[0.0, 0.16],
                range=[0, 100],
                fixedrange=True,
                showgrid=True,
                gridcolor="#e2e8f0",
                zeroline=False,
            ),
        )
        fig.add_hline(y=70, line_dash="dot", line_color="#dc2626", opacity=0.55, yref="y3")
        fig.add_hline(y=30, line_dash="dot", line_color="#059669", opacity=0.55, yref="y3")

    return fig


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
            Build watchlists, add tickers, reorder your stocks, and review fixed-position candlestick charts with long-horizon indicators calculated from full historical data.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------
# Main-page controls
# ------------------------------------------------------------
watchlist_names = list(st.session_state.watchlists.keys())
if st.session_state.active_watchlist not in watchlist_names and watchlist_names:
    st.session_state.active_watchlist = watchlist_names[0]

control_left, control_mid, control_right = st.columns([1.05, 1.05, 1.2])

with control_left:
    st.markdown('<div class="panel-title">Watchlist selection</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-subtitle">Choose or create your lists.</div>', unsafe_allow_html=True)

    selected = st.selectbox(
        "Active watchlist",
        watchlist_names,
        index=watchlist_names.index(st.session_state.active_watchlist),
    )
    st.session_state.active_watchlist = selected

    new_watchlist = st.text_input("New watchlist name", placeholder="e.g. Dividend Picks")
    if st.button("＋ Create watchlist", use_container_width=True):
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

with control_mid:
    st.markdown('<div class="panel-title">Manage selected list</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-subtitle">Rename the current list or remove it.</div>', unsafe_allow_html=True)

    rename_value = st.text_input("Rename selected watchlist", value=st.session_state.active_watchlist)
    rename_col, delete_col = st.columns(2)

    with rename_col:
        if st.button("Rename", use_container_width=True):
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

    with delete_col:
        if st.button("Delete", use_container_width=True, disabled=len(st.session_state.watchlists) <= 1):
            st.session_state.watchlists.pop(st.session_state.active_watchlist, None)
            st.session_state.active_watchlist = next(iter(st.session_state.watchlists.keys()))
            save_watchlists(st.session_state.watchlists)
            st.rerun()

with control_right:
    st.markdown('<div class="panel-title">Market data settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-subtitle">Indicators use full history; period only controls the visible chart range.</div>', unsafe_allow_html=True)

    settings_col1, settings_col2 = st.columns(2)
    with settings_col1:
        period = st.selectbox("Visible period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=1)
    with settings_col2:
        interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

    indicator_col1, indicator_col2, indicator_col3 = st.columns(3)
    with indicator_col1:
        show_sma20 = st.toggle("SMA 20", value=True)
        show_sma50 = st.toggle("SMA 50", value=False)
    with indicator_col2:
        show_sma100 = st.toggle("SMA 100", value=False)
        show_sma200 = st.toggle("SMA 200", value=False)
    with indicator_col3:
        show_bollinger = st.toggle("Bollinger Bands", value=False)
        show_volume = st.toggle("Volume", value=True)

    show_rsi = st.toggle("RSI 14", value=False)

    if st.button("Refresh market data", use_container_width=True):
        fetch_stock_history.clear()
        st.rerun()

indicator_settings = {
    "SMA20": show_sma20,
    "SMA50": show_sma50,
    "SMA100": show_sma100,
    "SMA200": show_sma200,
    "Bollinger Bands": show_bollinger,
}

st.divider()

# ------------------------------------------------------------
# Main watchlist area
# ------------------------------------------------------------
active = st.session_state.active_watchlist
symbols = st.session_state.watchlists.get(active, [])

list_title_col, add_symbol_col = st.columns([1.1, 1])

with list_title_col:
    st.subheader(active)
    st.caption(f"{len(symbols)} stock(s) in this watchlist")

with add_symbol_col:
    with st.form("add_symbol_form", clear_on_submit=True):
        symbol_input = st.text_input(
            "Add stock ticker",
            placeholder="AAPL, TSLA, BHP.AX, CBA.AX, BTC-USD",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Add stock", use_container_width=True)

    if submitted:
        symbol = normalize_symbol(symbol_input)
        if not symbol:
            st.warning("Please enter a ticker symbol.")
        elif symbol in symbols:
            st.info(f"{symbol} is already in {active}.")
        else:
            st.session_state.watchlists[active].append(symbol)
            save_watchlists(st.session_state.watchlists)
            st.rerun()

st.divider()

if not symbols:
    st.info("This watchlist is empty. Add a ticker above to show its candlestick chart.")
else:
    for index, symbol in enumerate(symbols):
        chart_col, action_col = st.columns([0.86, 0.14])

        with action_col:
            st.write("")
            st.write("")
            move_up_disabled = index == 0
            move_down_disabled = index == len(symbols) - 1

            if st.button("↑ Up", key=f"up-{active}-{symbol}", use_container_width=True, disabled=move_up_disabled):
                move_symbol(active, symbol, -1)
                st.rerun()

            if st.button("↓ Down", key=f"down-{active}-{symbol}", use_container_width=True, disabled=move_down_disabled):
                move_symbol(active, symbol, 1)
                st.rerun()

            if st.button("Remove", key=f"remove-{active}-{symbol}", use_container_width=True):
                st.session_state.watchlists[active] = [item for item in symbols if item != symbol]
                save_watchlists(st.session_state.watchlists)
                st.rerun()

        with chart_col:
            with st.container(border=True):
                with st.spinner(f"Loading {symbol} from yfinance..."):
                    full_df = fetch_stock_history(symbol, interval)

                if full_df.empty:
                    st.error(f"No data found for {symbol}. Check the ticker symbol or interval.")
                    continue

                display_df = filter_display_period(full_df, period)

                if len(full_df) < 200 and show_sma200:
                    st.caption(f"{symbol}: SMA 200 needs at least 200 data points. Available: {len(full_df)}.")

                fig = create_candlestick_chart(
                    symbol=symbol,
                    full_df=full_df,
                    display_df=display_df,
                    indicator_settings=indicator_settings,
                    show_volume=show_volume,
                    show_rsi=show_rsi,
                )
                st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

st.caption(
    "Data is provided through yfinance/Yahoo Finance. This dashboard is for educational and informational use only, not financial advice."
)
