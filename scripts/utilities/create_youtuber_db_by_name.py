#!/usr/bin/env python3
"""
Create databases for a specific YouTuber by name.
Creates two new databases:
- youtube_analysis_2years_single_{suffix}.db
- youtube_analysis_3months_single_{suffix}.db
"""

import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime


def get_youtuber_count(db_path, youtuber_name):
    """Get the count of records for a specific YouTuber."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM Youtuber_Financial_Data WHERE youtuber = ?",
        (youtuber_name,)
    )
    count = cursor.fetchone()[0]
    conn.close()

    return count


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
        return 0

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

    return len(financial_data)


def main():
    parser = argparse.ArgumentParser(
        description='Create single-YouTuber databases for a specific YouTuber'
    )
    parser.add_argument(
        'youtuber_name',
        help='Full name of the YouTuber (e.g., "Tom Nash")'
    )
    parser.add_argument(
        '--suffix',
        default=None,
        help='Suffix for output database files (default: auto-generated from name)'
    )

    args = parser.parse_args()

    # Generate suffix from name if not provided
    if args.suffix is None:
        # Take first word of name and lowercase
        args.suffix = args.youtuber_name.split()[0].lower()

    base_path = Path(__file__).parent.parent

    # Database paths
    db_2years = base_path / "youtube_analysis_2years.db"
    db_3months = base_path / "youtube_analysis_3months.db"

    # Output database paths
    db_2years_single = base_path / f"youtube_analysis_2years_single_{args.suffix}.db"
    db_3months_single = base_path / f"youtube_analysis_3months_single_{args.suffix}.db"

    # Check if source databases exist
    if not db_2years.exists():
        print(f"Error: {db_2years} not found!")
        sys.exit(1)

    if not db_3months.exists():
        print(f"Error: {db_3months} not found!")
        sys.exit(1)

    print("=" * 60)
    print(f"Creating databases for: {args.youtuber_name}")
    print(f"Output suffix: {args.suffix}")
    print("=" * 60)

    # Check record counts first
    count_2years = get_youtuber_count(db_2years, args.youtuber_name)
    count_3months = get_youtuber_count(db_3months, args.youtuber_name)

    if count_2years == 0 and count_3months == 0:
        print(f"\n✗ No records found for YouTuber: {args.youtuber_name}")
        print("\nAvailable YouTubers in 2years database:")
        conn = sqlite3.connect(db_2years)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT youtuber, COUNT(*) as count
            FROM Youtuber_Financial_Data
            WHERE youtuber IS NOT NULL
            GROUP BY youtuber
            ORDER BY count DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]} records")
        conn.close()
        sys.exit(1)

    print(f"\nFound records:")
    print(f"  2years database: {count_2years} records")
    print(f"  3months database: {count_3months} records")
    print()

    # Process 2years database
    if count_2years > 0:
        print("1. Creating 2years single database...")
        created_2years = create_single_youtuber_db(db_2years, db_2years_single, args.youtuber_name)
    else:
        print("1. Skipping 2years database (no records)")
        created_2years = 0

    # Process 3months database
    if count_3months > 0:
        print("2. Creating 3months single database...")
        created_3months = create_single_youtuber_db(db_3months, db_3months_single, args.youtuber_name)
    else:
        print("2. Skipping 3months database (no records)")
        created_3months = 0

    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    if created_2years > 0:
        print(f"✓ Created: {db_2years_single.name}")
        print(f"  YouTuber: {args.youtuber_name}")
        print(f"  Records: {created_2years}")
        print()
    if created_3months > 0:
        print(f"✓ Created: {db_3months_single.name}")
        print(f"  YouTuber: {args.youtuber_name}")
        print(f"  Records: {created_3months}")
    print("=" * 60)


if __name__ == "__main__":
    main()
