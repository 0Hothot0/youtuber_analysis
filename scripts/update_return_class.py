#!/usr/bin/env python3
"""
Batch update script for return_rate and class columns
Calculates 3-month stock returns using Yahoo Finance data
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from core.stock_price_fetcher import StockPriceFetcher


def update_return_class(limit: int | None = None, skip_existing: bool = True):
    """
    Update return_rate and class for all records

    Args:
        limit: Maximum number of records to process (None = all)
        skip_existing: Skip records that already have return_rate
    """
    print("="*80)
    print("Batch Update: return_rate and class columns")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize
    db = DatabaseManager()
    db.connect()
    fetcher = StockPriceFetcher(retry_delay=1.0)

    try:
        # Step 1: Count records to process
        print("\n" + "="*80)
        print("Step 1: Counting records")
        print("="*80)

        if skip_existing:
            query = """
                SELECT COUNT(*) as count
                FROM Youtuber_Financial_Data
                WHERE return_rate IS NULL
                  AND stock_ticker IS NOT NULL
                  AND published_time IS NOT NULL
            """
        else:
            query = """
                SELECT COUNT(*) as count
                FROM Youtuber_Financial_Data
                WHERE stock_ticker IS NOT NULL
                  AND published_time IS NOT NULL
            """

        db.cursor.execute(query)
        total_records = db.cursor.fetchone()['count']

        if limit:
            total_records = min(total_records, limit)

        print(f"Records to process: {total_records}")
        if total_records == 0:
            print("\nNo records to update. Exiting.")
            return

        # Step 2: Fetch records
        print("\n" + "="*80)
        print("Step 2: Fetching records")
        print("="*80)

        if skip_existing:
            query = """
                SELECT id, video_id, stock_ticker, published_time
                FROM Youtuber_Financial_Data
                WHERE return_rate IS NULL
                  AND stock_ticker IS NOT NULL
                  AND published_time IS NOT NULL
            """
        else:
            query = """
                SELECT id, video_id, stock_ticker, published_time
                FROM Youtuber_Financial_Data
                WHERE stock_ticker IS NOT NULL
                  AND published_time IS NOT NULL
            """

        if limit:
            query += f" LIMIT {limit}"

        db.cursor.execute(query)
        records = db.cursor.fetchall()
        print(f"✓ Fetched {len(records)} records")

        # Step 3: Process records
        print("\n" + "="*80)
        print("Step 3: Calculating returns")
        print("="*80)

        success_count = 0
        fail_count = 0
        skip_count = 0

        for idx, record in enumerate(records, 1):
            record_id = record['id']
            ticker = record['stock_ticker']
            published_time = record['published_time']
            video_id = record['video_id']

            print(f"\n[{idx}/{len(records)}] ID: {record_id} | {ticker} | {video_id[:11]}")
            print(f"  Published: {published_time}")

            # Calculate return
            result = fetcher.calculate_3month_return(ticker, published_time)

            if result:
                return_rate, classification = result
                print(f"  ✓ Return: {return_rate*100:.2f}% | Class: {classification}")

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
        if skip_count > 0:
            print(f"  ⊘ Skipped: {skip_count}")

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
            print(f"\n{'Ticker':<8} {'Date':<12} {'Return':<10} {'Class'}")
            print("-" * 45)
            for row in results:
                ticker = row['stock_ticker'] or 'N/A'
                date = row['published_time'][:10] if row['published_time'] else 'N/A'
                return_val = f"{row['return_rate']*100:.2f}%" if row['return_rate'] is not None else 'N/A'
                class_val = row['class'] if row['class'] is not None else 'N/A'
                print(f"{ticker:<8} {date:<12} {return_val:<10} {class_val}")
        else:
            print("No results to display")

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
    parser = argparse.ArgumentParser(
        description='Batch update return_rate and class columns using Yahoo Finance data'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of records to process (default: all)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recalculation for all records (including existing values)'
    )

    args = parser.parse_args()

    print(f"\nConfiguration:")
    print(f"  Limit: {args.limit if args.limit else 'No limit (process all)'}")
    print(f"  Skip existing: {not args.force}")

    if not args.limit and not args.force:
        print("\n⚠️  Warning: This will process ALL records without return_rate.")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)

    update_return_class(limit=args.limit, skip_existing=not args.force)
