# Stock Watchlist Dashboard

A Streamlit app using **yfinance** and **Plotly** to create custom stock watchlists and display candlestick charts for every stock in the selected watchlist.

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
stock-dashboard/
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
