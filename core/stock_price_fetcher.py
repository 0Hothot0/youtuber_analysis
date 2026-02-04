#!/usr/bin/env python3
"""
Stock Price Fetcher using yfinance (Yahoo Finance API)
Calculates 3-month return rates for stock analysis
"""

import yfinance as yf
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time


class StockPriceFetcher:
    """Fetches stock prices and calculates returns using Yahoo Finance"""

    def __init__(self, retry_delay=1.0):
        """
        Initialize the stock price fetcher

        Args:
            retry_delay: Delay in seconds between API calls to avoid rate limiting
        """
        self.retry_delay = retry_delay

    def get_price_on_date(self, ticker: str, target_date: datetime) -> float | None:
        """
        Get the closing price of a stock on a specific date

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
            target_date: Target date for the price

        Returns:
            Closing price as float, or None if not available
        """
        try:
            # Add small buffer to ensure we get the date we want
            start_date = target_date - timedelta(days=7)  # Look back 7 days
            end_date = target_date + timedelta(days=7)    # Look forward 7 days

            # Fetch data
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"    ⚠️  No price data found for {ticker} around {target_date.date()}")
                return None

            # Find the closest trading day to the target date
            hist.index = hist.index.tz_localize(None)  # Remove timezone info
            closest_date = min(hist.index, key=lambda x: abs(x - target_date))
            price = hist.loc[closest_date]['Close']

            # Check if the closest date is too far from target
            date_diff = abs((closest_date - target_date).days)
            if date_diff > 7:
                print(f"    ⚠️  Closest trading day for {ticker} is {date_diff} days away from target")
                return None

            return float(price)

        except Exception as e:
            print(f"    ❌ Error fetching price for {ticker}: {e}")
            return None

    def calculate_custom_return(self, ticker: str, publish_date: str | datetime, months: int = 3, threshold: float = 0.05) -> tuple[float, int] | None:
        """
        Calculate return rate for a custom time period and classification

        Args:
            ticker: Stock ticker symbol
            publish_date: Video publish date (string or datetime)
            months: Number of months for the return period (default: 3)
            threshold: Classification threshold (default: 0.05 = 5%)

        Returns:
            Tuple of (return_rate, class) where:
                - return_rate: Percentage return as decimal (e.g., 0.05 = 5%)
                - class: 1 if return >= threshold, else 0
            Returns None if calculation fails
        """
        try:
            # Parse publish date if string
            if isinstance(publish_date, str):
                # Try multiple date formats
                for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        start_date = datetime.strptime(publish_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    print(f"    ⚠️  Could not parse date: {publish_date}")
                    return None
            else:
                start_date = publish_date

            # Calculate end date (custom months)
            end_date = start_date + relativedelta(months=months)

            # Check if end date is in the future
            if end_date > datetime.now():
                print(f"    ⚠️  End date {end_date.date()} is in the future, cannot calculate return")
                return None

            # Get prices
            start_price = self.get_price_on_date(ticker, start_date)
            if start_price is None:
                return None

            # Small delay to avoid rate limiting
            time.sleep(self.retry_delay)

            end_price = self.get_price_on_date(ticker, end_date)
            if end_price is None:
                return None

            # Calculate return rate
            return_rate = (end_price - start_price) / start_price

            # Classify: 1 if >= threshold, else 0
            classification = 1 if return_rate >= threshold else 0

            return (return_rate, classification)

        except Exception as e:
            print(f"    ❌ Error calculating return for {ticker}: {e}")
            return None

    def calculate_3month_return(self, ticker: str, publish_date: str | datetime) -> tuple[float, int] | None:
        """
        Calculate 3-month return rate and classification (backward compatibility)

        Args:
            ticker: Stock ticker symbol
            publish_date: Video publish date (string or datetime)

        Returns:
            Tuple of (return_rate, class) where:
                - return_rate: Percentage return as decimal (e.g., 0.05 = 5%)
                - class: 1 if return >= 5%, else 0
            Returns None if calculation fails
        """
        return self.calculate_custom_return(ticker, publish_date, months=3, threshold=0.05)

    def batch_calculate(self, records: list[dict], rate_limit_delay: float = 2.0) -> dict:
        """
        Calculate returns for multiple records with rate limiting

        Args:
            records: List of dicts with 'stock_ticker' and 'published_time'
            rate_limit_delay: Delay between each record to avoid rate limits

        Returns:
            Dict mapping record IDs to (return_rate, class) tuples
        """
        results = {}
        total = len(records)

        for idx, record in enumerate(records, 1):
            record_id = record.get('id')
            ticker = record.get('stock_ticker')
            published_time = record.get('published_time')

            print(f"\n[{idx}/{total}] Processing {ticker} (ID: {record_id})")
            print(f"  Published: {published_time}")

            if not ticker or not published_time:
                print("  ⚠️  Missing ticker or published_time, skipping")
                continue

            result = self.calculate_3month_return(ticker, published_time)

            if result:
                return_rate, classification = result
                results[record_id] = (return_rate, classification)
                print(f"  ✓ Return: {return_rate*100:.2f}% | Class: {classification}")
            else:
                print(f"  ✗ Failed to calculate return")

            # Rate limiting
            if idx < total:
                time.sleep(rate_limit_delay)

        return results


def test_fetcher():
    """Test the stock price fetcher with known examples"""
    print("="*80)
    print("Testing StockPriceFetcher")
    print("="*80)

    fetcher = StockPriceFetcher()

    # Test case 1: AAPL on a known date
    print("\nTest 1: AAPL 3-month return from 2024-01-15")
    result = fetcher.calculate_3month_return('AAPL', '2024-01-15')
    if result:
        return_rate, classification = result
        print(f"  ✓ Return: {return_rate*100:.2f}% | Class: {classification}")
    else:
        print("  ✗ Failed")

    # Test case 2: TSLA on a known date
    print("\nTest 2: TSLA 3-month return from 2023-06-01")
    result = fetcher.calculate_3month_return('TSLA', '2023-06-01')
    if result:
        return_rate, classification = result
        print(f"  ✓ Return: {return_rate*100:.2f}% | Class: {classification}")
    else:
        print("  ✗ Failed")

    # Test case 3: Invalid ticker
    print("\nTest 3: Invalid ticker (INVALID123)")
    result = fetcher.calculate_3month_return('INVALID123', '2024-01-15')
    if result:
        return_rate, classification = result
        print(f"  ✓ Return: {return_rate*100:.2f}% | Class: {classification}")
    else:
        print("  ✗ Failed (expected)")

    # Test case 4: Future date
    print("\nTest 4: Future date (should fail)")
    result = fetcher.calculate_3month_return('AAPL', '2026-06-01')
    if result:
        return_rate, classification = result
        print(f"  ✓ Return: {return_rate*100:.2f}% | Class: {classification}")
    else:
        print("  ✗ Failed (expected)")

    print("\n" + "="*80)
    print("Test completed")
    print("="*80)


if __name__ == '__main__':
    test_fetcher()
