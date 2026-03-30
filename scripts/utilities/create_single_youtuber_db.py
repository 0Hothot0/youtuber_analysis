#!/usr/bin/env python3
"""
Create new databases containing only the YouTuber with the most data.
Creates two new databases:
- youtube_analysis_2years_single.db (from 2years database)
- youtube_analysis_3months_single.db (from 3months database)
"""

import sqlite3
import sys
from pathlib import Path

def get_top_youtuber(db_path):
    """Find the YouTuber with the most financial data records."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to find YouTuber with most records in Youtuber_Financial_Data
    query = """
    SELECT
        youtuber,
        COUNT(*) as record_count
    FROM Youtuber_Financial_Data
    WHERE youtuber IS NOT NULL
    GROUP BY youtuber
    ORDER BY record_count DESC
    LIMIT 1
    """

    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0], result[1]
    return None, 0

def create_single_youtuber_db(source_db, target_db, youtuber_name):
    """Create a new database with only one YouTuber's data."""
    # Connect to both databases
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    print(f"Creating new database: {target_db}")
    print(f"Copying data for YouTuber: {youtuber_name}")

    # Get the schema and create tables
    source_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = source_cursor.fetchall()

    for table_sql in tables:
        if table_sql[0]:
            target_cursor.execute(table_sql[0])

    # Try to copy youtubers table entry
    source_cursor.execute("SELECT * FROM youtubers WHERE name = ?", (youtuber_name,))
    youtuber_data = source_cursor.fetchone()

    if youtuber_data:
        youtuber_id = youtuber_data[0]
        source_cursor.execute("PRAGMA table_info(youtubers)")
        columns = [col[1] for col in source_cursor.fetchall()]
        placeholders = ','.join(['?' for _ in columns])
        target_cursor.execute(f"INSERT INTO youtubers VALUES ({placeholders})", youtuber_data)
        print(f"✓ Copied YouTuber: {youtuber_name} (ID: {youtuber_id})")
    else:
        # YouTuber not found in youtubers table, try fuzzy match or create new entry
        source_cursor.execute("SELECT * FROM youtubers WHERE name LIKE ?", (f"%{youtuber_name.split()[0]}%",))
        similar = source_cursor.fetchone()

        if similar:
            source_cursor.execute("PRAGMA table_info(youtubers)")
            columns = [col[1] for col in source_cursor.fetchall()]
            placeholders = ','.join(['?' for _ in columns])
            target_cursor.execute(f"INSERT INTO youtubers VALUES ({placeholders})", similar)
            print(f"✓ Copied similar YouTuber: {similar[1]} (original: {youtuber_name})")
        else:
            # Create a new entry
            from datetime import datetime
            new_id = 1
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            target_cursor.execute("INSERT INTO youtubers (id, name, created_at) VALUES (?, ?, ?)",
                                 (new_id, youtuber_name, created_at))
            print(f"✓ Created new YouTuber entry: {youtuber_name}")

    # Copy search_tags
    source_cursor.execute("SELECT * FROM search_tags")
    tags = source_cursor.fetchall()
    if tags:
        source_cursor.execute("PRAGMA table_info(search_tags)")
        columns = [col[1] for col in source_cursor.fetchall()]
        placeholders = ','.join(['?' for _ in columns])
        for tag in tags:
            try:
                target_cursor.execute(f"INSERT INTO search_tags VALUES ({placeholders})", tag)
            except sqlite3.IntegrityError:
                # Skip duplicates
                pass
        print(f"✓ Copied {len(tags)} search tags")

    # Copy Youtuber_Financial_Data (filter by youtuber field)
    source_cursor.execute("SELECT * FROM Youtuber_Financial_Data WHERE youtuber = ?", (youtuber_name,))
    financial_data = source_cursor.fetchall()

    if not financial_data:
        print(f"✗ No financial data found for YouTuber: {youtuber_name}")
        source_conn.close()
        target_conn.close()
        return

    # Get unique video_ids from financial data
    video_ids = list(set([row[2] for row in financial_data]))  # video_id is at index 2

    # Copy financial data
    source_cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    columns = [col[1] for col in source_cursor.fetchall()]
    placeholders = ','.join(['?' for _ in columns])
    for data in financial_data:
        target_cursor.execute(f"INSERT INTO Youtuber_Financial_Data VALUES ({placeholders})", data)
    print(f"✓ Copied {len(financial_data)} financial analysis records")

    # Copy videos (only videos that have financial data)
    if video_ids:
        placeholders_query = ','.join(['?' for _ in video_ids])
        source_cursor.execute(
            f"SELECT * FROM videos WHERE video_id IN ({placeholders_query})",
            video_ids
        )
        videos = source_cursor.fetchall()

        if videos:
            source_cursor.execute("PRAGMA table_info(videos)")
            columns = [col[1] for col in source_cursor.fetchall()]
            placeholders = ','.join(['?' for _ in columns])
            for video in videos:
                target_cursor.execute(f"INSERT INTO videos VALUES ({placeholders})", video)
            print(f"✓ Copied {len(videos)} videos")

    # Commit and close
    target_conn.commit()
    source_conn.close()
    target_conn.close()

    print(f"✓ Database created successfully: {target_db}\n")

def main():
    base_path = Path(__file__).parent.parent

    # Database paths
    db_2years = base_path / "youtube_analysis_2years.db"
    db_3months = base_path / "youtube_analysis_3months.db"

    # Output database paths
    db_2years_single = base_path / "youtube_analysis_2years_single.db"
    db_3months_single = base_path / "youtube_analysis_3months_single.db"

    # Check if source databases exist
    if not db_2years.exists():
        print(f"Error: {db_2years} not found!")
        sys.exit(1)

    if not db_3months.exists():
        print(f"Error: {db_3months} not found!")
        sys.exit(1)

    print("=" * 60)
    print("Finding YouTubers with most data...")
    print("=" * 60)

    # Process 2years database
    print("\n1. Analyzing 2years database...")
    youtuber_2years, count_2years = get_top_youtuber(db_2years)
    if youtuber_2years:
        print(f"   Top YouTuber: {youtuber_2years} ({count_2years} records)")
        create_single_youtuber_db(db_2years, db_2years_single, youtuber_2years)
    else:
        print("   No data found in 2years database!")

    # Process 3months database
    print("2. Analyzing 3months database...")
    youtuber_3months, count_3months = get_top_youtuber(db_3months)
    if youtuber_3months:
        print(f"   Top YouTuber: {youtuber_3months} ({count_3months} records)")
        create_single_youtuber_db(db_3months, db_3months_single, youtuber_3months)
    else:
        print("   No data found in 3months database!")

    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"Created: {db_2years_single.name}")
    print(f"  - YouTuber: {youtuber_2years}")
    print(f"  - Records: {count_2years}")
    print()
    print(f"Created: {db_3months_single.name}")
    print(f"  - YouTuber: {youtuber_3months}")
    print(f"  - Records: {count_3months}")
    print("=" * 60)

if __name__ == "__main__":
    main()
