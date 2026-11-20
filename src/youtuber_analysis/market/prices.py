"""Historical stock prices from Yahoo Finance (yfinance)."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta

import yfinance as yf
from dateutil.relativedelta import relativedelta

DATE_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d")


def parse_date(value: str | date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date: {value!r}")


class StockPriceFetcher:
    def __init__(self, delay_seconds: float = 1.0, max_gap_days: int = 7):
        self.delay_seconds = delay_seconds
        self.max_gap_days = max_gap_days

    def price_on(self, ticker: str, target: datetime) -> float | None:
        """Closing price on the trading day closest to ``target`` (within 7 days)."""
        try:
            hist = yf.Ticker(ticker).history(
                start=target - timedelta(days=self.max_gap_days),
                end=target + timedelta(days=self.max_gap_days),
            )
        except Exception as e:  # noqa: BLE001
            print(f"    price error {ticker} {target.date()}: {e}")
            return None
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None)
        closest = min(hist.index, key=lambda d: abs(d - target))
        if abs((closest - target).days) > self.max_gap_days:
            return None
        return float(hist.loc[closest]["Close"])

    def period_return(self, ticker: str, start: str | date | datetime, months: int) -> float | None:
        """Return from ``start`` to ``start + months``; None if unavailable or in the future."""
        start_dt = parse_date(start)
        end_dt = start_dt + relativedelta(months=months)
        if end_dt > datetime.now():
            return None

        start_price = self.price_on(ticker, start_dt)
        if start_price is None:
            return None
        time.sleep(self.delay_seconds)
        end_price = self.price_on(ticker, end_dt)
        if end_price is None:
            return None
        return (end_price - start_price) / start_price
