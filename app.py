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
    page_title="Stock Watchlist Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

WATCHLIST_FILE = Path("watchlists.json")
DEFAULT_WATCHLISTS = {
    "AI Leaders": ["NVDA", "MSFT", "AMD"],
    "Mega Cap Tech": ["AAPL", "GOOGL", "AMZN"],
}

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(circle at top left, #164e63 0%, #020617 35%, #020617 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        .hero-card {
            padding: 1.5rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 1.5rem;
            background: rgba(2, 6, 23, 0.78);
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
        }
        .small-muted {
            color: #94a3b8;
            font-size: 0.95rem;
        }
        h1, h2, h3 {
            color: #f8fafc;
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


# ------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_history(symbol: str, period: str, interval: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]

    date_col = "date" if "date" in df.columns else "datetime"
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.rename(columns={date_col: "date"})

    required = ["date", "open", "high", "low", "close", "volume"]
    return df[required].dropna()


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def create_candlestick_chart(
    symbol: str,
    df: pd.DataFrame,
    show_sma20: bool,
    show_ema9: bool,
    show_volume: bool,
    show_rsi: bool,
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=symbol,
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
            increasing_fillcolor="#22c55e",
            decreasing_fillcolor="#ef4444",
        )
    )

    if show_sma20 and len(df) >= 20:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["close"].rolling(20).mean(),
                mode="lines",
                name="SMA 20",
                line=dict(color="#38bdf8", width=2),
            )
        )

    if show_ema9 and len(df) >= 9:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["close"].ewm(span=9, adjust=False).mean(),
                mode="lines",
                name="EMA 9",
                line=dict(color="#f59e0b", width=2),
            )
        )

    if show_volume:
        colors = ["#22c55e" if row.close >= row.open else "#ef4444" for row in df.itertuples()]
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.28,
                yaxis="y2",
            )
        )

    if show_rsi and len(df) >= 14:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=calculate_rsi(df["close"]),
                mode="lines",
                name="RSI 14",
                line=dict(color="#a78bfa", width=2),
                yaxis="y3",
            )
        )

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest
    change_pct = ((latest["close"] - previous["close"]) / previous["close"]) * 100 if previous["close"] else 0

    fig.update_layout(
        title=f"{symbol} · ${latest['close']:.2f} · {change_pct:+.2f}%",
        template="plotly_dark",
        height=520 if show_rsi else 460,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(2, 6, 23, 0)",
        plot_bgcolor="rgba(15, 23, 42, 0.45)",
        font=dict(color="#e2e8f0"),
        xaxis=dict(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.12)",
        ),
        yaxis=dict(
            title="Price",
            domain=[0.28 if show_rsi else 0.18, 1.0],
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.12)",
        ),
        yaxis2=dict(
            title="Volume",
            domain=[0.0, 0.16],
            showgrid=False,
            visible=show_volume,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    if show_rsi:
        fig.update_layout(
            yaxis=dict(domain=[0.42, 1.0]),
            yaxis2=dict(domain=[0.22, 0.34], visible=show_volume, showgrid=False),
            yaxis3=dict(
                title="RSI",
                domain=[0.0, 0.16],
                range=[0, 100],
                showgrid=True,
                gridcolor="rgba(148, 163, 184, 0.12)",
            ),
        )
        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", opacity=0.5, yref="y3")
        fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", opacity=0.5, yref="y3")

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
        <p class="small-muted">📈 Streamlit + yfinance + Plotly</p>
        <h1>Stock Watchlist Dashboard</h1>
        <p class="small-muted">
            Create custom watchlists, rename them, add tickers, and view real candlestick charts for every stock in the selected watchlist.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------
# Sidebar controls
# ------------------------------------------------------------
with st.sidebar:
    st.header("Watchlists")

    watchlist_names = list(st.session_state.watchlists.keys())
    if st.session_state.active_watchlist not in watchlist_names and watchlist_names:
        st.session_state.active_watchlist = watchlist_names[0]

    selected = st.radio(
        "Select watchlist",
        watchlist_names,
        index=watchlist_names.index(st.session_state.active_watchlist),
        label_visibility="collapsed",
    )
    st.session_state.active_watchlist = selected

    st.divider()

    st.subheader("Create watchlist")
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

    st.divider()

    st.subheader("Manage selected")
    rename_value = st.text_input("Rename watchlist", value=st.session_state.active_watchlist)
    col_rename, col_delete = st.columns(2)

    with col_rename:
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

    with col_delete:
        if st.button("Delete", use_container_width=True, disabled=len(st.session_state.watchlists) <= 1):
            st.session_state.watchlists.pop(st.session_state.active_watchlist, None)
            st.session_state.active_watchlist = next(iter(st.session_state.watchlists.keys()))
            save_watchlists(st.session_state.watchlists)
            st.rerun()

    st.divider()

    st.subheader("Chart settings")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)
    show_sma20 = st.toggle("SMA 20", value=True)
    show_ema9 = st.toggle("EMA 9", value=True)
    show_volume = st.toggle("Volume", value=True)
    show_rsi = st.toggle("RSI 14", value=False)

    if st.button("Refresh market data", use_container_width=True):
        fetch_stock_history.clear()
        st.rerun()

# ------------------------------------------------------------
# Main watchlist area
# ------------------------------------------------------------
active = st.session_state.active_watchlist
symbols = st.session_state.watchlists.get(active, [])

left, right = st.columns([1.2, 1])

with left:
    st.subheader(active)
    st.caption(f"{len(symbols)} stock(s) in this watchlist")

with right:
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
    for symbol in symbols:
        chart_col, action_col = st.columns([0.88, 0.12])

        with action_col:
            st.write("")
            st.write("")
            if st.button("Remove", key=f"remove-{active}-{symbol}", use_container_width=True):
                st.session_state.watchlists[active] = [item for item in symbols if item != symbol]
                save_watchlists(st.session_state.watchlists)
                st.rerun()

        with chart_col:
            with st.container(border=True):
                with st.spinner(f"Loading {symbol} from yfinance..."):
                    df = fetch_stock_history(symbol, period, interval)

                if df.empty:
                    st.error(f"No data found for {symbol}. Check the ticker symbol or interval.")
                    continue

                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                change = latest["close"] - prev["close"]
                change_pct = (change / prev["close"] * 100) if prev["close"] else 0

                metric_cols = st.columns(4)
                metric_cols[0].metric("Last price", f"${latest['close']:.2f}", f"{change_pct:+.2f}%")
                metric_cols[1].metric("Open", f"${latest['open']:.2f}")
                metric_cols[2].metric("High", f"${latest['high']:.2f}")
                metric_cols[3].metric("Volume", f"{latest['volume']:,.0f}")

                fig = create_candlestick_chart(
                    symbol=symbol,
                    df=df,
                    show_sma20=show_sma20,
                    show_ema9=show_ema9,
                    show_volume=show_volume,
                    show_rsi=show_rsi,
                )
                st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Data is provided through yfinance/Yahoo Finance. This dashboard is for educational and informational use only, not financial advice."
)
