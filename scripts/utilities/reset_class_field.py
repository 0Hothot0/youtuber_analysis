#!/usr/bin/env python3
"""
Reset class field in both single YouTuber databases.
New rule:
- return_rate >= 0 (up or flat) -> class = 1
- return_rate < 0 (down) -> class = -1
"""

import sqlite3

def reset_class_field(db_path):
    """Reset class field based on return_rate."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"\n{'='*60}")
    print(f"Updating: {db_path}")
    print(f"{'='*60}")

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
        print(f"⚠ Warning: {null_count} records have NULL return_rate, class set to NULL")

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
    print(f"\n📈 Return rate statistics:")
    print(f"   Min: {stats[0]:.4f}")
    print(f"   Max: {stats[1]:.4f}")
    print(f"   Avg: {stats[2]:.4f}")

    # Sample verification
    print(f"\n🔍 Sample verification (5 records):")
    cursor.execute("""
        SELECT stock_ticker, return_rate, class
        FROM Youtuber_Financial_Data
        WHERE return_rate IS NOT NULL
        ORDER BY return_rate DESC
        LIMIT 5
    """)
    samples = cursor.fetchall()
    for stock, ret, cls in samples:
        status = "✅" if (ret >= 0 and cls == 1) or (ret < 0 and cls == -1) else "❌"
        print(f"   {status} {stock}: return_rate={ret:.4f}, class={cls}")

    # Commit changes
    conn.commit()
    conn.close()

    print(f"✓ Database updated successfully!")

    return up_count, down_count, null_count

def main():
    print("="*60)
    print("Resetting class field in both databases")
    print("="*60)
    print("Rule:")
    print("  return_rate >= 0 (up or flat) -> class = 1")
    print("  return_rate < 0 (down) -> class = -1")

    # Update both databases
    db1 = "youtube_analysis_2years_single.db"
    db2 = "youtube_analysis_3months_single.db"

    up1, down1, null1 = reset_class_field(db1)
    up2, down2, null2 = reset_class_field(db2)

    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"\n{db1}:")
    print(f"  class=1 (up/flat): {up1} records")
    print(f"  class=-1 (down): {down1} records")
    if null1 > 0:
        print(f"  class=NULL: {null1} records")

    print(f"\n{db2}:")
    print(f"  class=1 (up/flat): {up2} records")
    print(f"  class=-1 (down): {down2} records")
    if null2 > 0:
        print(f"  class=NULL: {null2} records")

    print("\n" + "="*60)
    print("✅ All class fields have been reset successfully!")
    print("="*60)

if __name__ == "__main__":
    main()
