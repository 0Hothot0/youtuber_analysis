#!/usr/bin/env python3
"""
Automated Pipeline to Reach 200 Analyzed Videos
"""
import os
import sys
import time
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Define YouTubers to search
YOUTUBERS = [
    "Invest with Henry",
    "Financial Education",
    "Meet Kevin",
    "Andrei Jikh",
    "Graham Stephan",
    "Joseph Carlson",
    "Everything Money",
    "Dividend Data",
    "Stock Brotha",
    "Brandon Beavis Investing"
]

# Search keywords for each phase
SEARCH_KEYWORDS = [
    "investing",
    "stock market",
    "portfolio",
    "stocks",
    "analysis"
]

def check_status():
    """Check the current status of video analysis"""
    conn = sqlite3.connect('youtube_analysis.db')
    cursor = conn.cursor()

    # Get total videos
    cursor.execute('SELECT COUNT(*) FROM videos')
    total = cursor.fetchone()[0]

    # Get count of distinct analyzed videos
    cursor.execute('''
        SELECT COUNT(DISTINCT video_id)
        FROM Youtuber_Financial_Data
    ''')
    analyzed = cursor.fetchone()[0]

    # Get unanalyzed videos
    cursor.execute('''
        SELECT COUNT(*)
        FROM videos v
        WHERE NOT EXISTS (
            SELECT 1 FROM Youtuber_Financial_Data f
            WHERE f.video_id = v.video_id
        )
    ''')
    unanalyzed = cursor.fetchone()[0]

    conn.close()
    return total, analyzed, unanalyzed

def print_status(phase_name):
    """Print current status"""
    total, analyzed, unanalyzed = check_status()
    print(f"\n{'='*80}")
    print(f"{phase_name}")
    print(f"{'='*80}")
    print(f"Total videos in database: {total}")
    print(f"Videos analyzed (distinct): {analyzed}")
    print(f"Videos unanalyzed: {unanalyzed}")
    print(f"Videos needed to reach 200: {max(0, 200 - analyzed)}")
    print(f"Progress: {analyzed}/200 ({analyzed/200*100:.1f}%)")
    print(f"{'='*80}\n")

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n>>> {description}")
    print(f">>> Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def phase1_analyze_existing():
    """Phase 1: Analyze all unanalyzed videos in database"""
    print_status("PHASE 1: Analyzing Existing Videos")

    total, analyzed, unanalyzed = check_status()

    if unanalyzed == 0:
        print("No unanalyzed videos found. Skipping Phase 1.")
        return True

    print(f"Analyzing {unanalyzed} unanalyzed videos...")

    # Run batch analysis
    cmd = ["python3", "gemini_analyzer.py", "--batch", "--limit", str(unanalyzed)]
    success = run_command(cmd, f"Analyzing {unanalyzed} videos")

    print_status("PHASE 1 COMPLETE")
    return success

def phase2_search_more_videos(max_videos_per_search=15):
    """Phase 2: Search for more videos"""
    print_status("PHASE 2: Searching for More Videos")

    total, analyzed, unanalyzed = check_status()
    videos_needed = 200 - analyzed - unanalyzed

    if videos_needed <= 0:
        print("Already have enough videos in database. Skipping Phase 2.")
        return True

    print(f"Need approximately {videos_needed} more videos")
    print(f"Will search for videos from {len(YOUTUBERS)} YouTubers with {len(SEARCH_KEYWORDS)} keywords each")

    search_count = 0
    for youtuber in YOUTUBERS:
        for keyword in SEARCH_KEYWORDS:
            search_query = f"{youtuber} {keyword}"
            cmd = [
                "python3", "youtube_search.py",
                search_query,
                "--save-db",
                "--youtuber", youtuber,
                "--max-results", str(max_videos_per_search),
                "--min-age", "2"
            ]

            print(f"\n[{search_count + 1}/{len(YOUTUBERS) * len(SEARCH_KEYWORDS)}] Searching: {search_query}")
            run_command(cmd, f"Searching: {search_query}")

            search_count += 1

            # Wait between searches to respect rate limits
            if search_count < len(YOUTUBERS) * len(SEARCH_KEYWORDS):
                print("Waiting 3 seconds before next search...")
                time.sleep(3)

            # Check if we have enough videos now
            total, analyzed, unanalyzed = check_status()
            if (analyzed + unanalyzed) >= 200:
                print(f"\nReached sufficient videos ({analyzed + unanalyzed}). Stopping search.")
                break

        if (analyzed + unanalyzed) >= 200:
            break

    print_status("PHASE 2 COMPLETE")
    return True

def phase3_analyze_new_videos():
    """Phase 3: Analyze newly found videos"""
    print_status("PHASE 3: Analyzing New Videos")

    total, analyzed, unanalyzed = check_status()

    if unanalyzed == 0:
        print("No unanalyzed videos found. Skipping Phase 3.")
        return True

    # Analyze in batches of 50
    batch_size = 50
    remaining = unanalyzed

    while remaining > 0:
        current_batch = min(batch_size, remaining)
        print(f"\nAnalyzing batch of {current_batch} videos (Remaining: {remaining})")

        cmd = ["python3", "gemini_analyzer.py", "--batch", "--limit", str(current_batch)]
        success = run_command(cmd, f"Analyzing {current_batch} videos")

        if not success:
            print("Batch analysis failed. Continuing anyway...")

        # Update status
        total, analyzed, unanalyzed = check_status()
        remaining = unanalyzed

        # Check if we've reached target
        if analyzed >= 200:
            print(f"\n🎉 Reached target! {analyzed} videos analyzed.")
            break

        # Wait between batches
        if remaining > 0:
            print("Waiting 5 seconds before next batch...")
            time.sleep(5)

    print_status("PHASE 3 COMPLETE")
    return True

def phase4_cycle_until_target():
    """Phase 4: Cycle through search and analysis until target is reached"""
    print_status("PHASE 4: Cycling Until Target Reached")

    max_cycles = 10  # Safety limit
    cycle = 0

    while cycle < max_cycles:
        total, analyzed, unanalyzed = check_status()

        if analyzed >= 200:
            print(f"\n🎉 TARGET REACHED! {analyzed} videos analyzed.")
            break

        cycle += 1
        print(f"\n{'='*80}")
        print(f"CYCLE {cycle}/{max_cycles}")
        print(f"{'='*80}")

        # If we have unanalyzed videos, analyze them first
        if unanalyzed > 0:
            print(f"Analyzing {unanalyzed} unanalyzed videos...")
            phase3_analyze_new_videos()
        else:
            # Search for more videos
            print("No unanalyzed videos. Searching for more...")
            phase2_search_more_videos(max_videos_per_search=15)

            # Then analyze them
            phase3_analyze_new_videos()

        # Check status again
        total, analyzed, unanalyzed = check_status()
        if analyzed >= 200:
            print(f"\n🎉 TARGET REACHED! {analyzed} videos analyzed.")
            break

    print_status("PHASE 4 COMPLETE")
    return True

def generate_final_report():
    """Generate final report with statistics"""
    print(f"\n{'='*80}")
    print("FINAL REPORT")
    print(f"{'='*80}")

    conn = sqlite3.connect('youtube_analysis.db')
    cursor = conn.cursor()

    # Total videos
    cursor.execute('SELECT COUNT(*) FROM videos')
    total = cursor.fetchone()[0]

    # Analyzed videos
    cursor.execute('SELECT COUNT(DISTINCT video_id) FROM Youtuber_Financial_Data')
    analyzed = cursor.fetchone()[0]

    # Total analysis records
    cursor.execute('SELECT COUNT(*) FROM Youtuber_Financial_Data')
    total_records = cursor.fetchone()[0]

    # Top 20 stock tickers
    cursor.execute('''
        SELECT stock_ticker, COUNT(*) as count
        FROM Youtuber_Financial_Data
        WHERE stock_ticker IS NOT NULL AND stock_ticker != ''
        GROUP BY stock_ticker
        ORDER BY count DESC
        LIMIT 20
    ''')
    top_tickers = cursor.fetchall()

    print(f"\nDatabase Statistics:")
    print(f"  Total videos in database: {total}")
    print(f"  Videos analyzed (distinct): {analyzed}")
    print(f"  Total analysis records: {total_records}")
    print(f"  Average stocks per video: {total_records/analyzed:.2f}" if analyzed > 0 else "  Average stocks per video: N/A")

    print(f"\nTop 20 Most Mentioned Stock Tickers:")
    print(f"{'='*80}")
    print(f"{'Rank':<6} {'Ticker':<10} {'Count':<10}")
    print(f"{'-'*80}")
    for rank, (ticker, count) in enumerate(top_tickers, 1):
        print(f"{rank:<6} {ticker:<10} {count:<10}")

    print(f"\n{'='*80}")
    print(f"Target Status: {'✓ ACHIEVED' if analyzed >= 200 else '✗ NOT REACHED'} ({analyzed}/200)")
    print(f"{'='*80}\n")

    conn.close()

def main():
    """Main pipeline execution"""
    print("\n" + "="*80)
    print("YOUTUBE VIDEO ANALYSIS PIPELINE")
    print("Target: 200 analyzed videos")
    print("="*80 + "\n")

    start_time = time.time()

    # Initial status
    print_status("INITIAL STATUS")

    try:
        # Phase 1: Analyze existing unanalyzed videos
        phase1_analyze_existing()

        # Check if we've reached target
        total, analyzed, unanalyzed = check_status()
        if analyzed >= 200:
            print(f"\n🎉 Target reached after Phase 1! {analyzed} videos analyzed.")
        else:
            # Phase 2: Search for more videos
            phase2_search_more_videos()

            # Phase 3: Analyze new videos
            phase3_analyze_new_videos()

            # Check if we've reached target
            total, analyzed, unanalyzed = check_status()
            if analyzed < 200:
                # Phase 4: Continue cycling
                phase4_cycle_until_target()

        # Generate final report
        generate_final_report()

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        print_status("STATUS AT INTERRUPTION")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        print_status("STATUS AT ERROR")

    end_time = time.time()
    duration = end_time - start_time
    print(f"\nTotal execution time: {duration/60:.1f} minutes ({duration:.0f} seconds)")

if __name__ == '__main__':
    main()
