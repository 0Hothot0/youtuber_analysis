# YouTube Financial Video Analysis Pipeline

Executes the complete pipeline for analyzing YouTube financial videos with multi-stock support.

## Pipeline Steps

### 1. Data Import
Import YouTubers and search tags from configuration file.

### 2. Video Search
Search for financial videos from each YouTuber, filtering for videos 2+ years old.

### 3. Video Analysis
Analyze videos with Gemini AI to extract financial insights and stock mentions.

## Usage

Run the complete pipeline:
```bash
# Full pipeline with default settings
./run_analysis_pipeline.sh

# Or step by step:
python3 data_importer.py youtuber.txt
python3 youtube_search.py "{youtuber} stock" --save-db --max-results 10 --min-age 2
python3 gemini_analyzer.py --batch --limit 20
```

## Configuration

Edit `youtuber.txt` to add/remove YouTubers and tags:
- Lines 1-10: YouTuber names (one per line)
- Lines 11+: Comma-separated search tags

## Multi-Stock Analysis

The new system supports analyzing multiple stocks per video:
- Each video can have multiple stock records (one per primary stock)
- Videos are assigned a unique UUID
- All stocks from the same video share the same UUID
- Composite unique constraint on (video_id, stock_ticker)

## Database Schema

**Youtuber_Financial_Data:**
- `video_uuid` - Unique identifier per video
- `video_id` - YouTube video ID (not unique)
- `stock_ticker` - Stock symbol (nullable for legacy data)
- 17 financial analysis fields
- `comment_sentiment` - Always 0 (placeholder)

## Output

Results are stored in `youtube_analysis.db`:
- `youtubers` - List of YouTubers
- `search_tags` - Search keywords
- `videos` - Video metadata
- `Youtuber_Financial_Data` - Analysis results

## Monitoring

Check progress:
```bash
python3 monitor_progress.py
```

View statistics:
```bash
python3 -c "from db_manager import DatabaseManager; db = DatabaseManager(); db.connect(); stats = db.get_statistics(); print(stats); db.close()"
```

## Important Notes

- **API Keys Required:**
  - `YOUTUBE_API_KEY` - For video search
  - `GOOGLE_CLOUD_PROJECT` - For Gemini AI analysis

- **Rate Limits:**
  - YouTube: 10,000 units/day
  - Wait 2-3 seconds between API calls

- **Video Age Filter:**
  - Default: 2 years (`--min-age 2`)
  - Filters videos published before 2023-12-25

- **Backup:**
  - Database is automatically backed up before migrations
  - Latest: `youtube_analysis_backup_*.db`
