#!/usr/bin/env python3
"""
Clean up low-coverage feature columns from single databases.

Removes 8 columns with <50% coverage (except stock_price_growth_trend which user wants to keep).
Keeps 24 essential columns that are universal or user-specified.

Target databases:
- youtube_analysis_2years_single.db
- youtube_analysis_3months_single.db
"""

import sqlite3
import sys
from pathlib import Path

# Columns to keep (25 total)
COLUMNS_TO_KEEP = [
    # Basic fields (5)
    'id',
    'video_uuid',
    'video_id',
    'stock_ticker',
    'youtuber',

    # Video metrics (4)
    'like_number',
    'comment_number',
    'view_number',
    'published_time',

    # Analysis results (9)
    'text_type',
    'video_sentiment',
    'comment_sentiment',
    'financial_ratio',
    'relevancy',
    'short_term_focus',
    'celebrity',
    'long_term_competitiveness',
    'stock_price_growth_trend',  # User specified to keep despite 52.8% coverage

    # Target variables (3)
    'return_rate',
    'class',
    'during',

    # System fields (3)
    'raw_json',
    'created_at',
    'updated_at'
]

# Columns being removed (8 total)
COLUMNS_TO_REMOVE = [
    'policy_impact',           # 10.6% coverage
    'earnings_expectation_gap', # 17.9% coverage
    'target_price',            # 22.8% coverage
    'valuation',               # 28.5% coverage
    'market_capitalization',   # 31.7% coverage
    'ceo_leadership_style',    # 32.5% coverage
    'financial_health',        # 46.3% coverage
    'market_demand'            # 48.0% coverage
]


def cleanup_database(db_path: str):
    """Clean up a single database by removing low-coverage columns."""
    print(f"\n{'='*60}")
    print(f"Processing: {db_path}")
    print(f"{'='*60}")

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Step 1: Get current schema
        cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
        old_columns = cursor.fetchall()
        old_column_count = len(old_columns)
        print(f"\n📊 Current columns: {old_column_count}")

        # Step 2: Verify columns to remove exist
        old_column_names = [col[1] for col in old_columns]
        missing_columns = [col for col in COLUMNS_TO_REMOVE if col not in old_column_names]
        if missing_columns:
            print(f"⚠️  Warning: Columns not found: {missing_columns}")

        # Step 3: Get record count before
        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
        record_count = cursor.fetchone()[0]
        print(f"📝 Total records: {record_count}")

        # Step 4: Build column definitions for new table
        columns_sql = []
        for col in old_columns:
            col_name = col[1]
            if col_name not in COLUMNS_TO_KEEP:
                continue

            col_type = col[2]
            col_notnull = col[3]
            col_default = col[4]
            col_pk = col[5]

            # Build column definition parts
            parts = [col_name, col_type]

            if col_pk:
                parts.append("PRIMARY KEY AUTOINCREMENT")
            elif col_notnull:
                parts.append("NOT NULL")

            if col_default is not None and not col_pk:
                # Handle special SQLite functions in DEFAULT
                if col_default.startswith("datetime("):
                    parts.append(f"DEFAULT (datetime('now'))")
                else:
                    parts.append(f"DEFAULT {col_default}")

            columns_sql.append(' '.join(parts))

        print(f"\n🎯 Keeping {len(columns_sql)} columns")
        print(f"🗑️  Removing {len(COLUMNS_TO_REMOVE)} columns: {', '.join(COLUMNS_TO_REMOVE)}")

        # Step 5: Create new table with only desired columns
        create_sql = f"""
        CREATE TABLE Youtuber_Financial_Data_new (
            {',\n            '.join(columns_sql)},
            UNIQUE(video_id, stock_ticker)
        )
        """
        cursor.execute(create_sql)

        # Step 6: Copy data (only kept columns)
        column_names = ', '.join(COLUMNS_TO_KEEP)
        cursor.execute(f"""
            INSERT INTO Youtuber_Financial_Data_new ({column_names})
            SELECT {column_names}
            FROM Youtuber_Financial_Data
        """)

        # Step 7: Drop old table and rename new one
        cursor.execute("DROP TABLE Youtuber_Financial_Data")
        cursor.execute("ALTER TABLE Youtuber_Financial_Data_new RENAME TO Youtuber_Financial_Data")

        # Step 8: Verify results
        cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
        new_columns = cursor.fetchall()
        new_column_count = len(new_columns)

        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
        new_record_count = cursor.fetchone()[0]

        conn.commit()

        # Report results
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   Columns: {old_column_count} → {new_column_count} (removed {old_column_count - new_column_count})")
        print(f"   Records: {record_count} → {new_record_count} (lost {record_count - new_record_count})")

        if new_column_count != len(COLUMNS_TO_KEEP):
            print(f"⚠️  Warning: Expected {len(COLUMNS_TO_KEEP)} columns, got {new_column_count}")

        if new_record_count != record_count:
            print(f"⚠️  Warning: Record count changed!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    """Clean up both single databases."""
    print("🧹 Database Feature Cleanup Script")
    print(f"📋 Target: Remove {len(COLUMNS_TO_REMOVE)} low-coverage columns")
    print(f"✅ Keep: {len(COLUMNS_TO_KEEP)} universal/essential columns")

    databases = [
        'youtube_analysis_2years_single.db',
        'youtube_analysis_3months_single.db'
    ]

    success_count = 0
    for db_path in databases:
        if cleanup_database(db_path):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"📊 Final Summary")
    print(f"{'='*60}")
    print(f"✅ Successfully cleaned: {success_count}/{len(databases)} databases")

    if success_count == len(databases):
        print("\n🎉 All databases cleaned successfully!")
        print("\n📋 Columns removed:")
        for i, col in enumerate(COLUMNS_TO_REMOVE, 1):
            print(f"   {i}. {col}")
        print("\n💡 Tip: Backups are available as *_backup.db files")
        return 0
    else:
        print("\n⚠️  Some databases failed to clean")
        return 1


if __name__ == '__main__':
    sys.exit(main())
