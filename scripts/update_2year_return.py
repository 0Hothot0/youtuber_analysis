#!/usr/bin/env python3
"""
Update 2-year return rate and class in youtube_analysis_2years.db
Calculates stock returns 24 months after video publish date

NEW Classification Logic (Prediction Accuracy):
- video_sentiment > 0 (positive) + return_rate >= 5% → class = 1
- video_sentiment = 0 (neutral) + -5% < return_rate < 5% → class = 1
- video_sentiment < 0 (negative) + return_rate <= -5% → class = 1
- All other cases → class = -1

Where class=1 means correct prediction, class=-1 means incorrect prediction
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from core.stock_price_fetcher import StockPriceFetcher


def calculate_class(sentiment: float, return_rate: float) -> int:
    """
    Calculate class based on sentiment and return rate (NEW LOGIC)

    Args:
        sentiment: Video sentiment score
        return_rate: 2-year stock return rate (as decimal, e.g., 0.05 = 5%)

    Returns:
        1 if prediction is correct, -1 if incorrect
    """
    if sentiment > 0 and return_rate >= 0.05:
        return 1
    elif sentiment == 0 and -0.05 < return_rate < 0.05:
        return 1
    elif sentiment < 0 and return_rate <= -0.05:
        return 1
    else:
        return -1


def update_2year_return():
    """
    Update return_rate and class for 2-year period in youtube_analysis_2years.db
    """
    print("="*80)
    print("Batch Update: 2-Year return_rate and class")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: youtube_analysis_2years.db")
    print(f"Time Period: 24 months (2 years)")
    print(f"Classification: Based on sentiment vs return correlation")

    # Initialize with 2years database
    db = DatabaseManager(db_path='youtube_analysis_2years.db')
    db.connect()
    fetcher = StockPriceFetcher(retry_delay=1.0)

    try:
        # Step 1: Count records to process
        print("\n" + "="*80)
        print("Step 1: Counting records")
        print("="*80)

        query = """
            SELECT COUNT(*) as count
            FROM Youtuber_Financial_Data
            WHERE stock_ticker IS NOT NULL
              AND stock_ticker != 'N/A'
              AND published_time IS NOT NULL
        """

        db.cursor.execute(query)
        total_records = db.cursor.fetchone()['count']

        print(f"Records to process: {total_records}")
        if total_records == 0:
            print("\nNo records to update. Exiting.")
            return

        # Step 2: Fetch records
        print("\n" + "="*80)
        print("Step 2: Fetching records")
        print("="*80)

        query = """
            SELECT id, video_id, stock_ticker, published_time, video_sentiment
            FROM Youtuber_Financial_Data
            WHERE stock_ticker IS NOT NULL
              AND stock_ticker != 'N/A'
              AND published_time IS NOT NULL
        """

        db.cursor.execute(query)
        records = db.cursor.fetchall()
        print(f"✓ Fetched {len(records)} records")

        # Step 3: Process records
        print("\n" + "="*80)
        print("Step 3: Calculating 2-year returns")
        print("="*80)

        success_count = 0
        fail_count = 0

        for idx, record in enumerate(records, 1):
            record_id = record['id']
            ticker = record['stock_ticker']
            published_time = record['published_time']
            video_id = record['video_id']
            sentiment = record['video_sentiment']

            print(f"\n[{idx}/{len(records)}] ID: {record_id} | {ticker} | {video_id[:11]}")
            print(f"  Published: {published_time}")
            print(f"  Sentiment: {sentiment}")

            # Calculate 2-year return (24 months)
            result = fetcher.calculate_custom_return(ticker, published_time, months=24, threshold=0.05)

            if result:
                return_rate, _ = result  # Ignore old classification

                # Calculate NEW class based on sentiment vs return
                classification = calculate_class(sentiment, return_rate)

                print(f"  ✓ 2-Year Return: {return_rate*100:+.2f}% | Class: {classification}")

                # Update database
                db.cursor.execute("""
                    UPDATE Youtuber_Financial_Data
                    SET return_rate = ?,
                        class = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (return_rate, classification, record_id))

                db.conn.commit()
                success_count += 1
            else:
                print(f"  ✗ Failed to calculate return")
                fail_count += 1

        # Step 4: Summary
        print("\n" + "="*80)
        print("Step 4: Summary")
        print("="*80)
        print(f"Total processed: {len(records)}")
        print(f"  ✓ Success: {success_count}")
        print(f"  ✗ Failed: {fail_count}")

        # Show sample results
        print("\n" + "="*80)
        print("Sample results (first 5)")
        print("="*80)
        db.cursor.execute("""
            SELECT stock_ticker, published_time, return_rate, class
            FROM Youtuber_Financial_Data
            WHERE return_rate IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        results = db.cursor.fetchall()

        if results:
            print(f"\n{'Ticker':<8} {'Date':<12} {'2Y-Return':<12} {'Class'}")
            print("-" * 50)
            for row in results:
                ticker = row['stock_ticker'] or 'N/A'
                date = row['published_time'][:10] if row['published_time'] else 'N/A'
                return_val = f"{row['return_rate']*100:.2f}%" if row['return_rate'] is not None else 'N/A'
                class_val = row['class'] if row['class'] is not None else 'N/A'
                print(f"{ticker:<8} {date:<12} {return_val:<12} {class_val}")
        else:
            print("No results to display")

        # Final statistics
        print("\n" + "="*80)
        print("Final Statistics")
        print("="*80)
        db.cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END) as correct_predictions,
                SUM(CASE WHEN class = -1 THEN 1 ELSE 0 END) as incorrect_predictions,
                AVG(return_rate) as avg_return
            FROM Youtuber_Financial_Data
            WHERE return_rate IS NOT NULL
        """)
        stats = db.cursor.fetchone()

        print(f"Total records: {stats['total']}")
        print(f"  Class  1 (Correct prediction): {stats['correct_predictions']} ({stats['correct_predictions']/stats['total']*100:.1f}%)")
        print(f"  Class -1 (Incorrect prediction): {stats['incorrect_predictions']} ({stats['incorrect_predictions']/stats['total']*100:.1f}%)")
        if stats['avg_return']:
            print(f"Average 2-year return: {stats['avg_return']*100:.2f}%")

        # Prediction accuracy
        accuracy = stats['correct_predictions'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"\nPrediction Accuracy: {accuracy:.2f}%")

        print("\n" + "="*80)
        print("Update completed!")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        db.conn.rollback()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.conn.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Update 2-year return rates and classifications')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    print("\n⚠️  This will update youtube_analysis_2years.db with 2-year return rates.")
    print("    Classification logic: sentiment vs return correlation")
    print("    - Positive sentiment + ≥5% return = Correct (class=1)")
    print("    - Neutral sentiment + -5% to 5% return = Correct (class=1)")
    print("    - Negative sentiment + ≤-5% return = Correct (class=1)")
    print("    - All other cases = Incorrect (class=-1)")

    if not args.yes:
        response = input("\nContinue? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    else:
        print("\nAuto-confirmed with --yes flag")

    update_2year_return()
