#!/usr/bin/env python3
"""
Reset class field in ALL databases.
New rule:
- return_rate >= 0 (up or flat) -> class = 1
- return_rate < 0 (down) -> class = -1
"""

import sqlite3
import os
from pathlib import Path

def reset_class_field(db_path):
    """Reset class field based on return_rate."""

    if not os.path.exists(db_path):
        print(f"⚠ Database not found: {db_path}")
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"\n{'='*70}")
    print(f"Updating: {db_path}")
    print(f"{'='*70}")

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Youtuber_Financial_Data'")
    if not cursor.fetchone():
        print("⚠ Youtuber_Financial_Data table not found, skipping...")
        conn.close()
        return None

    # First, clear all existing class values
    cursor.execute("UPDATE Youtuber_Financial_Data SET class = NULL")
    print("✓ Cleared all existing class values")

    # Check total records
    cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
    total = cursor.fetchone()[0]
    print(f"Total records: {total}")

    # Update class based on return_rate
    # class = 1 for return_rate >= 0 (up or flat)
    cursor.execute("""
        UPDATE Youtuber_Financial_Data
        SET class = 1
        WHERE return_rate >= 0
    """)
    up_count = cursor.rowcount
    print(f"✓ Set class=1 for {up_count} records (return_rate >= 0)")

    # class = -1 for return_rate < 0 (down)
    cursor.execute("""
        UPDATE Youtuber_Financial_Data
        SET class = -1
        WHERE return_rate < 0
    """)
    down_count = cursor.rowcount
    print(f"✓ Set class=-1 for {down_count} records (return_rate < 0)")

    # Check for NULL return_rate
    cursor.execute("""
        SELECT COUNT(*) FROM Youtuber_Financial_Data
        WHERE return_rate IS NULL
    """)
    null_count = cursor.fetchone()[0]
    if null_count > 0:
        print(f"⚠ Warning: {null_count} records have NULL return_rate, class remains NULL")

    # Verify the update
    cursor.execute("""
        SELECT class, COUNT(*) as count
        FROM Youtuber_Financial_Data
        GROUP BY class
        ORDER BY class
    """)
    distribution = cursor.fetchall()

    print(f"\n📊 New class distribution:")
    for cls, cnt in distribution:
        if cls is None:
            print(f"   class=NULL: {cnt} records")
        else:
            print(f"   class={cls}: {cnt} records")

    # Show statistics
    cursor.execute("""
        SELECT
            MIN(return_rate) as min_ret,
            MAX(return_rate) as max_ret,
            AVG(return_rate) as avg_ret
        FROM Youtuber_Financial_Data
        WHERE return_rate IS NOT NULL
    """)
    stats = cursor.fetchone()
    if stats[0] is not None:
        print(f"\n📈 Return rate statistics:")
        print(f"   Min: {stats[0]:.4f}")
        print(f"   Max: {stats[1]:.4f}")
        print(f"   Avg: {stats[2]:.4f}")

    # Verify correctness
    cursor.execute("""
        SELECT
            SUM(CASE WHEN return_rate >= 0 AND class = 1 THEN 1 ELSE 0 END) as correct_positive,
            SUM(CASE WHEN return_rate < 0 AND class = -1 THEN 1 ELSE 0 END) as correct_negative,
            SUM(CASE WHEN (return_rate >= 0 AND class != 1) OR (return_rate < 0 AND class != -1) THEN 1 ELSE 0 END) as incorrect
        FROM Youtuber_Financial_Data
        WHERE return_rate IS NOT NULL
    """)
    verify = cursor.fetchone()

    if verify[2] == 0:
        print(f"\n✅ Verification: All records follow the new rule!")
    else:
        print(f"\n❌ Verification: {verify[2]} records don't follow the rule!")

    # Commit changes
    conn.commit()
    conn.close()

    print(f"✓ Database updated successfully!")

    return {
        'total': total,
        'up': up_count,
        'down': down_count,
        'null': null_count
    }

def main():
    print("="*70)
    print("Resetting class field in ALL databases")
    print("="*70)
    print("Rule:")
    print("  return_rate >= 0 (up or flat) -> class = 1")
    print("  return_rate < 0 (down) -> class = -1")

    # List of all databases
    databases = [
        "youtube_analysis.db",
        "youtube_analysis_2years.db",
        "youtube_analysis_3months.db",
        "youtube_analysis_2years_single.db",
        "youtube_analysis_3months_single.db"
    ]

    results = {}
    for db in databases:
        result = reset_class_field(db)
        if result:
            results[db] = result

    # Summary
    print("\n" + "="*70)
    print("Summary Report")
    print("="*70)

    for db, result in results.items():
        print(f"\n{db}:")
        print(f"  Total records: {result['total']}")
        print(f"  class=1 (up/flat): {result['up']} ({result['up']/result['total']*100:.1f}%)")
        print(f"  class=-1 (down): {result['down']} ({result['down']/result['total']*100:.1f}%)")
        if result['null'] > 0:
            print(f"  class=NULL: {result['null']} ({result['null']/result['total']*100:.1f}%)")

    print("\n" + "="*70)
    print(f"✅ Successfully updated {len(results)} databases!")
    print("="*70)

if __name__ == "__main__":
    main()
