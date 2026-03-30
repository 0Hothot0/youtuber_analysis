#!/usr/bin/env python3
"""
Compare two single YouTuber databases to ensure data consistency.
"""

import sqlite3

def compare_databases(db1_path, db2_path):
    """Compare two databases in detail."""

    conn1 = sqlite3.connect(db1_path)
    conn2 = sqlite3.connect(db2_path)

    cursor1 = conn1.cursor()
    cursor2 = conn2.cursor()

    print("="*70)
    print("Database Comparison Report")
    print("="*70)
    print(f"Database 1: {db1_path}")
    print(f"Database 2: {db2_path}")
    print("="*70)

    issues = []

    # 1. Compare YouTubers table
    print("\n1. Comparing youtubers table...")
    cursor1.execute("SELECT * FROM youtubers ORDER BY id")
    youtubers1 = cursor1.fetchall()
    cursor2.execute("SELECT * FROM youtubers ORDER BY id")
    youtubers2 = cursor2.fetchall()

    if youtubers1 == youtubers2:
        print("   ✅ YouTubers table: Identical")
    else:
        print("   ❌ YouTubers table: Different")
        print(f"      DB1: {youtubers1}")
        print(f"      DB2: {youtubers2}")
        issues.append("YouTubers table mismatch")

    # 2. Compare videos table
    print("\n2. Comparing videos table...")
    cursor1.execute("SELECT COUNT(*) FROM videos")
    video_count1 = cursor1.fetchone()[0]
    cursor2.execute("SELECT COUNT(*) FROM videos")
    video_count2 = cursor2.fetchone()[0]

    print(f"   DB1 videos: {video_count1}")
    print(f"   DB2 videos: {video_count2}")

    if video_count1 == video_count2:
        print("   ✅ Video count: Same")

        # Check if video_ids are the same
        cursor1.execute("SELECT video_id FROM videos ORDER BY video_id")
        video_ids1 = set([v[0] for v in cursor1.fetchall()])
        cursor2.execute("SELECT video_id FROM videos ORDER BY video_id")
        video_ids2 = set([v[0] for v in cursor2.fetchall()])

        if video_ids1 == video_ids2:
            print("   ✅ Video IDs: Identical")

            # Check if video content is the same
            cursor1.execute("SELECT video_id, title, published_at FROM videos ORDER BY video_id")
            videos1 = cursor1.fetchall()
            cursor2.execute("SELECT video_id, title, published_at FROM videos ORDER BY video_id")
            videos2 = cursor2.fetchall()

            if videos1 == videos2:
                print("   ✅ Video content: Identical")
            else:
                print("   ⚠ Video content: Some differences detected")
                # Find differences
                for i, (v1, v2) in enumerate(zip(videos1, videos2)):
                    if v1 != v2:
                        print(f"      Video {i+1} differs:")
                        print(f"        DB1: {v1}")
                        print(f"        DB2: {v2}")
                        if i >= 3:
                            print(f"      ... and more")
                            break
                issues.append("Video content differs")
        else:
            only_in_1 = video_ids1 - video_ids2
            only_in_2 = video_ids2 - video_ids1
            print(f"   ❌ Video IDs: Different")
            if only_in_1:
                print(f"      Only in DB1: {len(only_in_1)} videos")
                print(f"      Sample: {list(only_in_1)[:5]}")
            if only_in_2:
                print(f"      Only in DB2: {len(only_in_2)} videos")
                print(f"      Sample: {list(only_in_2)[:5]}")
            issues.append("Different video_ids")
    else:
        print("   ❌ Video count: Different")
        issues.append("Different video counts")

    # 3. Compare financial data table
    print("\n3. Comparing Youtuber_Financial_Data table...")
    cursor1.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
    fin_count1 = cursor1.fetchone()[0]
    cursor2.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
    fin_count2 = cursor2.fetchone()[0]

    print(f"   DB1 records: {fin_count1}")
    print(f"   DB2 records: {fin_count2}")

    if fin_count1 == fin_count2:
        print("   ✅ Record count: Same")

        # Check unique video_ids
        cursor1.execute("SELECT COUNT(DISTINCT video_id) FROM Youtuber_Financial_Data")
        unique1 = cursor1.fetchone()[0]
        cursor2.execute("SELECT COUNT(DISTINCT video_id) FROM Youtuber_Financial_Data")
        unique2 = cursor2.fetchone()[0]

        print(f"   DB1 unique videos: {unique1}")
        print(f"   DB2 unique videos: {unique2}")

        if unique1 == unique2:
            print("   ✅ Unique video count: Same")

            # Check if the actual records are the same
            cursor1.execute("""
                SELECT video_id, stock_ticker, video_sentiment, published_time
                FROM Youtuber_Financial_Data
                ORDER BY video_id, stock_ticker
            """)
            fin1 = cursor1.fetchall()
            cursor2.execute("""
                SELECT video_id, stock_ticker, video_sentiment, published_time
                FROM Youtuber_Financial_Data
                ORDER BY video_id, stock_ticker
            """)
            fin2 = cursor2.fetchall()

            if fin1 == fin2:
                print("   ✅ Financial data content: Identical")
            else:
                print("   ⚠ Financial data content: Some differences")
                diff_count = 0
                for i, (f1, f2) in enumerate(zip(fin1, fin2)):
                    if f1 != f2:
                        if diff_count < 3:
                            print(f"      Record {i+1} differs:")
                            print(f"        DB1: {f1}")
                            print(f"        DB2: {f2}")
                        diff_count += 1
                if diff_count > 3:
                    print(f"      ... and {diff_count - 3} more differences")
                issues.append("Financial data content differs")
        else:
            print("   ❌ Unique video count: Different")
            issues.append("Different unique video counts")
    else:
        print("   ❌ Record count: Different")
        issues.append("Different financial record counts")

    # 4. Check data consistency within each database
    print("\n4. Checking data consistency...")

    for db_path, cursor, name in [(db1_path, cursor1, "DB1"), (db2_path, cursor2, "DB2")]:
        cursor.execute("""
            SELECT COUNT(*)
            FROM Youtuber_Financial_Data yfd
            LEFT JOIN videos v ON yfd.video_id = v.video_id
            WHERE v.video_id IS NULL
        """)
        missing = cursor.fetchone()[0]

        if missing == 0:
            print(f"   ✅ {name}: All financial records have video metadata")
        else:
            print(f"   ❌ {name}: {missing} financial records missing video metadata")
            issues.append(f"{name} missing video metadata")

    # 5. Summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)

    if not issues:
        print("✅ DATABASES ARE IDENTICAL")
        print("   All tables, records, and content match perfectly!")
    else:
        print("⚠ DATABASES HAVE DIFFERENCES")
        print(f"   Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"   - {issue}")

    print("="*70)

    conn1.close()
    conn2.close()

    return len(issues) == 0

if __name__ == "__main__":
    db1 = "youtube_analysis_2years_single.db"
    db2 = "youtube_analysis_3months_single.db"

    is_identical = compare_databases(db1, db2)

    if is_identical:
        print("\n✅ The databases are ready for analysis!")
    else:
        print("\n⚠ Please review the differences above.")
