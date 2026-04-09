from __future__ import annotations

from datetime import date, datetime, timezone

import yfinance as yf

from morning_brief.config import Config
from morning_brief.fetchers.base import BaseFetcher, FetchResult

# Major indices: (ticker, label)
_INDICES = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "Nasdaq"),
    ("^DJI", "Dow"),
    ("^VIX", "VIX"),
    ("^TNX", "10Y Yield"),
]

_CRYPTO = [
    ("BTC-USD", "BTC"),
    ("ETH-USD", "ETH"),
]


def _pct_change(ticker_symbol: str) -> str:
    """Return a formatted '±X.XX%' string for the day's price change."""
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="2d")
        if len(hist) < 2:
            return "N/A"
        prev_close = hist["Close"].iloc[-2]
        last_close = hist["Close"].iloc[-1]
        pct = (last_close - prev_close) / prev_close * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.2f}%"
    except Exception:
        return "N/A"


def _price_and_pct(ticker_symbol: str) -> tuple[str, str]:
    """Return (price_str, pct_change_str)."""
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="2d")
        if len(hist) < 1:
            return "N/A", "N/A"
        last = hist["Close"].iloc[-1]
        price_str = f"${last:,.2f}" if last >= 1 else f"${last:.4f}"
        if len(hist) >= 2:
            prev = hist["Close"].iloc[-2]
            pct = (last - prev) / prev * 100
            sign = "+" if pct >= 0 else ""
            pct_str = f"{sign}{pct:.2f}%"
        else:
            pct_str = "N/A"
        return price_str, pct_str
    except Exception:
        return "N/A", "N/A"


def _qqqm_holdings(top_n: int) -> str:
    try:
        t = yf.Ticker("QQQM")
        holdings_df = t.funds_data.top_holdings
        if holdings_df is None or holdings_df.empty:
            return "QQQM holdings unavailable"
        lines = [f"QQQM Top {min(top_n, len(holdings_df))} Holdings:"]
        for symbol, row in holdings_df.head(top_n).iterrows():
            weight = row.get("Holding Percent", row.get("holdingPercent", None))
            if weight is not None:
                lines.append(f"  {symbol}: {weight * 100:.1f}%")
            else:
                lines.append(f"  {symbol}")
        return "\n".join(lines)
    except Exception as e:
        return f"QQQM holdings unavailable ({e})"


def _earnings_today() -> str:
    """Check a broad set of well-known tickers for earnings announcements today."""
    watch = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "NFLX",
        "AMD", "INTC", "QCOM", "AVGO", "CRM", "ORCL", "IBM", "ADBE",
        "JPM", "GS", "MS", "BAC", "WFC", "V", "MA",
        "JNJ", "PFE", "MRK", "UNH",
        "WMT", "COST", "TGT", "HD",
        "XOM", "CVX",
    ]
    today = date.today()
    reporting: list[str] = []
    for symbol in watch:
        try:
            cal = yf.Ticker(symbol).calendar
            if cal is None:
                continue
            # calendar may be a dict or DataFrame depending on yfinance version
            if hasattr(cal, "get"):
                earnings_date = cal.get("Earnings Date")
                if earnings_date is None:
                    continue
                # May be a list
                if isinstance(earnings_date, list):
                    for d in earnings_date:
                        if hasattr(d, "date"):
                            d = d.date()
                        if d == today:
                            reporting.append(symbol)
                            break
                else:
                    if hasattr(earnings_date, "date"):
                        earnings_date = earnings_date.date()
                    if earnings_date == today:
                        reporting.append(symbol)
        except Exception:
            continue
    if not reporting:
        return "No major earnings today"
    return "Earnings today: " + ", ".join(reporting)


class MarketFetcher(BaseFetcher):
    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self) -> FetchResult:
        try:
            lines: list[str] = []

            # --- Major indices ---
            lines.append("Market Indices:")
            for symbol, label in _INDICES:
                price, pct = _price_and_pct(symbol)
                lines.append(f"  {label}: {price} ({pct})")

            # --- QQQM ---
            qqqm_price, qqqm_pct = _price_and_pct("QQQM")
            lines.append(f"\nQQQM: {qqqm_price} ({qqqm_pct})")
            if self._config.enable_qqqm_holdings:
                lines.append(_qqqm_holdings(self._config.qqqm_top_n))

            # --- Crypto ---
            if self._config.enable_crypto:
                lines.append("\nCrypto:")
                for symbol, label in _CRYPTO:
                    price, pct = _price_and_pct(symbol)
                    lines.append(f"  {label}: {price} ({pct})")

            # --- User watchlist ---
            if self._config.stock_watchlist:
                lines.append("\nWatchlist:")
                for symbol in self._config.stock_watchlist:
                    price, pct = _price_and_pct(symbol)
                    lines.append(f"  {symbol}: {price} ({pct})")

            # --- Earnings today ---
            lines.append(f"\n{_earnings_today()}")

            return FetchResult(
                source_name="Market",
                content="\n".join(lines),
                success=True,
            )
        except Exception as e:
            return FetchResult(source_name="Market", content="", success=False, error=str(e))
