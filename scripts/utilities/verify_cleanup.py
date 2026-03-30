#!/usr/bin/env python3
"""
Verify the cleanup of single databases.

Checks:
1. Column count (should be 24)
2. Record count (should be 123)
3. Expected columns are present
4. Removed columns are absent
5. Sample data integrity
"""

import sqlite3
from pathlib import Path

# Expected columns after cleanup (24 total)
EXPECTED_COLUMNS = [
    'id', 'video_uuid', 'video_id', 'stock_ticker', 'youtuber',
    'like_number', 'comment_number', 'view_number', 'published_time',
    'text_type', 'video_sentiment', 'comment_sentiment', 'financial_ratio',
    'relevancy', 'short_term_focus', 'celebrity', 'long_term_competitiveness',
    'stock_price_growth_trend', 'return_rate', 'class', 'during',
    'raw_json', 'created_at', 'updated_at'
]

# Columns that should be removed (8 total)
REMOVED_COLUMNS = [
    'policy_impact', 'earnings_expectation_gap', 'target_price',
    'valuation', 'market_capitalization', 'ceo_leadership_style',
    'financial_health', 'market_demand'
]


def verify_database(db_path: str):
    """Verify a single database after cleanup."""
    print(f"\n{'='*60}")
    print(f"Verifying: {db_path}")
    print(f"{'='*60}")

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check 1: Column count and names
        cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        column_count = len(column_names)

        print(f"\n1️⃣  Column Count: {column_count}")
        if column_count == 24:
            print("   ✅ Correct (expected 24)")
        else:
            print(f"   ❌ Wrong (expected 24, got {column_count})")

        # Check 2: Expected columns present
        missing_columns = [col for col in EXPECTED_COLUMNS if col not in column_names]
        print(f"\n2️⃣  Expected Columns:")
        if not missing_columns:
            print("   ✅ All 24 expected columns present")
        else:
            print(f"   ❌ Missing columns: {missing_columns}")

        # Check 3: Removed columns absent
        still_present = [col for col in REMOVED_COLUMNS if col in column_names]
        print(f"\n3️⃣  Removed Columns:")
        if not still_present:
            print("   ✅ All 8 columns successfully removed")
        else:
            print(f"   ❌ These should be removed: {still_present}")

        # Check 4: Record count
        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
        record_count = cursor.fetchone()[0]
        print(f"\n4️⃣  Record Count: {record_count}")
        if record_count == 123:
            print("   ✅ Correct (expected 123)")
        else:
            print(f"   ⚠️  Expected 123, got {record_count}")

        # Check 5: Sample data integrity
        cursor.execute("""
            SELECT video_id, stock_ticker, video_sentiment, return_rate, youtuber
            FROM Youtuber_Financial_Data
            LIMIT 3
        """)
        sample_rows = cursor.fetchall()
        print(f"\n5️⃣  Sample Data (first 3 records):")
        for i, row in enumerate(sample_rows, 1):
            video_id, ticker, sentiment, return_rate, youtuber = row
            sentiment_str = f"{sentiment:.2f}" if sentiment is not None else "None"
            return_str = f"{return_rate:.2%}" if return_rate is not None else "None"
            ticker_str = ticker if ticker else "None"
            print(f"   {i}. {youtuber[:20]:20} | {ticker_str:8} | sentiment={sentiment_str:6} | return={return_str:8}")

        # Check 6: Critical columns not null
        cursor.execute("""
            SELECT COUNT(*) FROM Youtuber_Financial_Data
            WHERE video_uuid IS NULL OR video_id IS NULL
        """)
        null_count = cursor.fetchone()[0]
        print(f"\n6️⃣  Data Integrity:")
        if null_count == 0:
            print("   ✅ No NULL values in critical columns (video_uuid, video_id)")
        else:
            print(f"   ❌ Found {null_count} records with NULL critical columns")

        # Final verdict
        all_passed = (
            column_count == 24 and
            not missing_columns and
            not still_present and
            record_count == 123 and
            null_count == 0
        )

        print(f"\n{'='*60}")
        if all_passed:
            print("✅ VERIFICATION PASSED - Database cleanup successful!")
        else:
            print("⚠️  VERIFICATION ISSUES - Please review above")
        print(f"{'='*60}")

        return all_passed

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False
    finally:
        conn.close()


def main():
    """Verify both single databases."""
    print("🔍 Database Cleanup Verification")

    databases = [
        'youtube_analysis_2years_single.db',
        'youtube_analysis_3months_single.db'
    ]

    results = {}
    for db_path in databases:
        results[db_path] = verify_database(db_path)

    # Final summary
    print(f"\n{'='*60}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*60}")

    passed_count = sum(results.values())
    for db_path, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {db_path}")

    print(f"\nTotal: {passed_count}/{len(databases)} databases verified successfully")

    if passed_count == len(databases):
        print("\n🎉 All verifications passed! Cleanup was successful.")
        return 0
    else:
        print("\n⚠️  Some verifications failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
