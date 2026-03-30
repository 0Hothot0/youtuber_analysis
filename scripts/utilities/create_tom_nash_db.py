#!/usr/bin/env python3
"""
Create new databases containing only Tom Nash's data.
Creates two new databases:
- youtube_analysis_2years_single.db (from 2years database)
- youtube_analysis_3months_single.db (from 3months database)

For 3months database, missing video metadata will be filled from 2years database.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def create_tom_nash_db(source_db, target_db, db_name, video_source_db=None):
    """Create a new database with only Tom Nash's data."""
    youtuber_name = "Tom Nash"

    # Connect to databases
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    print(f"\n{'='*60}")
    print(f"Creating {db_name}")
    print(f"{'='*60}")

    # Get the schema and create tables
    source_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = source_cursor.fetchall()

    for table_sql in tables:
        if table_sql[0]:
            target_cursor.execute(table_sql[0])

    # Copy YouTuber
    source_cursor.execute("SELECT * FROM youtubers WHERE name = ?", (youtuber_name,))
    youtuber_data = source_cursor.fetchone()

    if youtuber_data:
        source_cursor.execute("PRAGMA table_info(youtubers)")
        columns = [col[1] for col in source_cursor.fetchall()]
        placeholders = ','.join(['?' for _ in columns])
        target_cursor.execute(f"INSERT INTO youtubers VALUES ({placeholders})", youtuber_data)
        print(f"✓ Copied YouTuber: {youtuber_name}")
    else:
        # Create new entry
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        target_cursor.execute("INSERT INTO youtubers (id, name, created_at) VALUES (?, ?, ?)",
                             (1, youtuber_name, created_at))
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
                pass
        print(f"✓ Copied {len(tags)} search tags")

    # Copy Youtuber_Financial_Data
    source_cursor.execute("SELECT * FROM Youtuber_Financial_Data WHERE youtuber = ?", (youtuber_name,))
    financial_data = source_cursor.fetchall()

    if not financial_data:
        print(f"✗ No financial data found for {youtuber_name}")
        source_conn.close()
        target_conn.close()
        return

    # Get unique video_ids
    video_ids = list(set([row[2] for row in financial_data]))

    # Copy financial data
    source_cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    columns = [col[1] for col in source_cursor.fetchall()]
    placeholders = ','.join(['?' for _ in columns])
    for data in financial_data:
        target_cursor.execute(f"INSERT INTO Youtuber_Financial_Data VALUES ({placeholders})", data)
    print(f"✓ Copied {len(financial_data)} financial analysis records")
    print(f"✓ Unique videos in financial data: {len(video_ids)}")

    # Copy videos from source or alternative source
    if video_ids:
        placeholders_query = ','.join(['?' for _ in video_ids])

        # First try to get videos from source database
        source_cursor.execute(
            f"SELECT * FROM videos WHERE video_id IN ({placeholders_query})",
            video_ids
        )
        videos = source_cursor.fetchall()

        videos_copied = 0
        if videos:
            source_cursor.execute("PRAGMA table_info(videos)")
            columns = [col[1] for col in source_cursor.fetchall()]
            placeholders = ','.join(['?' for _ in columns])
            for video in videos:
                target_cursor.execute(f"INSERT INTO videos VALUES ({placeholders})", video)
                videos_copied += 1
            print(f"✓ Copied {videos_copied} videos from source database")

        # If videos are missing and we have an alternative source
        missing_count = len(video_ids) - videos_copied
        if missing_count > 0 and video_source_db:
            print(f"⚠ {missing_count} videos missing in source, fetching from alternative source...")

            # Get missing video_ids
            existing_video_ids = [v[1] for v in videos]  # video_id is at index 1
            missing_video_ids = [vid for vid in video_ids if vid not in existing_video_ids]

            # Connect to alternative source
            alt_conn = sqlite3.connect(video_source_db)
            alt_cursor = alt_conn.cursor()

            placeholders_query = ','.join(['?' for _ in missing_video_ids])
            alt_cursor.execute(
                f"SELECT * FROM videos WHERE video_id IN ({placeholders_query})",
                missing_video_ids
            )
            alt_videos = alt_cursor.fetchall()

            if alt_videos:
                alt_cursor.execute("PRAGMA table_info(videos)")
                columns = [col[1] for col in alt_cursor.fetchall()]
                placeholders = ','.join(['?' for _ in columns])
                for video in alt_videos:
                    target_cursor.execute(f"INSERT INTO videos VALUES ({placeholders})", video)
                print(f"✓ Filled {len(alt_videos)} missing videos from alternative source")
            else:
                print(f"✗ Could not find missing videos in alternative source")

            alt_conn.close()

    # Commit and close
    target_conn.commit()

    # Final verification
    target_cursor.execute("SELECT COUNT(*) FROM videos")
    final_video_count = target_cursor.fetchone()[0]

    target_cursor.execute("SELECT COUNT(DISTINCT video_id) FROM Youtuber_Financial_Data")
    unique_financial_videos = target_cursor.fetchone()[0]

    print(f"\n📊 Final Statistics:")
    print(f"  Total videos in videos table: {final_video_count}")
    print(f"  Unique videos in financial data: {unique_financial_videos}")
    if final_video_count == unique_financial_videos:
        print(f"  ✅ All videos have complete metadata!")
    else:
        print(f"  ⚠ Missing {unique_financial_videos - final_video_count} videos metadata")

    source_conn.close()
    target_conn.close()

    print(f"✓ Database created: {target_db}")

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

    print("="*60)
    print("Creating Tom Nash Single YouTuber Databases")
    print("="*60)

    # Create 2years database (has complete data)
    create_tom_nash_db(
        db_2years,
        db_2years_single,
        "youtube_analysis_2years_single.db"
    )

    # Create 3months database (will fill missing videos from 2years)
    create_tom_nash_db(
        db_3months,
        db_3months_single,
        "youtube_analysis_3months_single.db",
        video_source_db=db_2years  # Use 2years as alternative source
    )

    print("\n" + "="*60)
    print("✅ All databases created successfully!")
    print("="*60)

if __name__ == "__main__":
    main()
