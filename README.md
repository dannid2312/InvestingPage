# Market Watchlist Dashboard

A professional Streamlit dashboard using **yfinance** and **Plotly** to manage custom stock watchlists and display fixed-position candlestick charts.

## Revisions included

- Charts are no longer draggable or accidentally zoomable.
- Plotly mode bar is hidden for a cleaner dashboard experience.
- Chart axes use fixed ranges to prevent accidental repositioning.
- The page now uses a clearer light professional theme with stronger text contrast.
- Removed the metric row above each chart: Last Price, Open, High, and Volume.
- Updated the header to a more professional market dashboard style.

## Features

- Create custom watchlists
- Rename and delete watchlists
- Add and remove ticker symbols
- Fetch real market data with `yfinance`
- Plotly candlestick charts
- Volume bars
- SMA 20, EMA 9, and RSI 14 indicator toggles
- Local persistence through `watchlists.json`

## Project structure

```txt
stock-dashboard-revised/
  app.py
  requirements.txt
  watchlists.json
  README.md
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit, usually:

```txt
http://localhost:8501
```

## Ticker examples

- US stocks: `AAPL`, `MSFT`, `NVDA`, `TSLA`
- ASX stocks: `BHP.AX`, `CBA.AX`, `WES.AX`
- Crypto: `BTC-USD`, `ETH-USD`

## Notes

- Data is provided through `yfinance` / Yahoo Finance.
- This dashboard is for educational and informational use only, not financial advice.
- If charts do not load, check your internet connection and confirm that the ticker symbol is valid.
