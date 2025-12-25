# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive YouTube financial video analysis system that:
1. Searches for financial videos from specified YouTubers
2. Analyzes videos using Google Gemini AI to extract financial insights
3. Supports multi-stock analysis (one video can discuss multiple stocks)
4. Stores structured analysis results in SQLite database

The system uses YouTube Data API v3 for video search and Google Vertex AI Gemini for video content analysis.

## Architecture

### Core Components

**1. Database Layer (`db_manager.py`)**
- SQLite database with 4 tables:
  - `youtubers` - List of financial YouTubers
  - `search_tags` - Search keywords/tags
  - `videos` - Video metadata from YouTube API
  - `Youtuber_Financial_Data` - Gemini AI analysis results

**2. Video Search (`youtube_search.py`)**
- `YouTubeSearcher` class for YouTube API interactions
- `search_videos()` - Searches with age filter (default: 2+ years old)
- `get_video_details()` - Fetches complete video metadata
- `save_to_database()` - Stores results in database

**3. AI Analysis (`gemini_analyzer.py`)**
- `GeminiVideoAnalyzer` class for Gemini AI integration
- `analyze_video()` - Returns list of stock analyses per video
- `save_analysis_to_db()` - Stores multi-stock results with UUID
- Supports analyzing multiple primary stocks per video

**4. Data Import (`data_importer.py`)**
- Imports YouTubers and tags from `youtuber.txt`
- Format: Lines 1-10 = YouTuber names, Lines 11+ = comma-separated tags

## Key Features (2025-12-25 Update)

### Multi-Stock Analysis
- **One Video, Multiple Stocks**: Each video can have multiple analysis records (one per primary stock)
- **Video UUID**: All stocks from the same video share a unique `video_uuid`
- **Composite Unique Key**: `(video_id, stock_ticker)` prevents duplicates
- **Primary Stock Detection**: Gemini AI filters out casually mentioned stocks

### Database Schema (`Youtuber_Financial_Data`)

Key fields (28 total):
- `video_uuid` TEXT NOT NULL - Unique identifier per video
- `video_id` TEXT NOT NULL - YouTube video ID (not unique)
- `stock_ticker` TEXT - Stock symbol (nullable for legacy data)
- `comment_sentiment` REAL DEFAULT 0 - Placeholder (always 0)
- 17 financial analysis fields (sentiment, ratios, market indicators)
- `raw_json` TEXT - Original Gemini response

### Gemini Prompt Strategy

The system uses a specialized prompt that:
1. Only analyzes PRIMARY stocks (significant discussion, charts, main topic)
2. Ignores brief mentions or comparisons
3. Returns JSON array format
4. Assigns 0 to unmentioned metrics (no inference)
5. Provides 17 structured financial indicators per stock

## Environment Setup

### Prerequisites
- Python 3.12+
- YouTube Data API v3 Key
- Google Cloud Project with Vertex AI enabled
- Gemini API access

### Installation
```bash
# Install dependencies
python3 -m pip install -r requirements.txt --user --break-system-packages

# Configure API keys
cp .env.example .env
# Edit .env and add:
#   YOUTUBE_API_KEY=your_youtube_key
#   GOOGLE_CLOUD_PROJECT=your_gcp_project
#   GOOGLE_CLOUD_LOCATION=us-central1
```

### Database Setup
```bash
# Initialize database
python3 db_manager.py

# Import YouTubers and tags
python3 data_importer.py youtuber.txt
```

## Running the Analysis Pipeline

### Complete Pipeline (Recommended)
```bash
# 1. Import data
python3 data_importer.py youtuber.txt

# 2. Search videos (2+ years old)
python3 youtube_search.py "YouTuber Name stock" --save-db --max-results 10 --min-age 2

# 3. Analyze videos
python3 gemini_analyzer.py --batch --limit 20
```

### Individual Operations

**Search videos:**
```bash
# Basic search
python3 youtube_search.py "tesla stock" --save-db

# Filter by age (2+ years)
python3 youtube_search.py "nvidia analysis" --save-db --max-results 20 --min-age 2
```

**Analyze videos:**
```bash
# Single video
python3 gemini_analyzer.py --video-id VIDEO_ID

# Batch analysis
python3 gemini_analyzer.py --batch --limit 10

# Specific YouTuber
python3 gemini_analyzer.py --batch --youtuber "Tom Nash" --limit 5
```

## API Quota Considerations

**YouTube Data API v3:**
- Daily limit: 10,000 units (default)
- `search.list`: ~100 units
- `videos.list`: ~1 unit per 50 videos
- Recommended: Wait 2-3 seconds between searches

**Google Vertex AI Gemini:**
- Uses Gemini 2.0 Flash (experimental)
- Temperature: 0.2 (consistent results)
- Max retries: 3 with exponential backoff
- Recommended: Wait 2 seconds between API calls

## Database Query Examples

```python
from db_manager import DatabaseManager

db = DatabaseManager()
db.connect()

# Get all stocks analyzed from one video
stocks = db.get_financial_data_by_uuid('video-uuid-here')
for stock in stocks:
    print(f"{stock['stock_ticker']}: {stock['video_sentiment']}")

# Get all analysis for a specific video_id
records = db.get_financial_data_by_video('YouTube_VIDEO_ID')

# Statistics
stats = db.get_statistics()
print(f"Videos: {stats['videos']}, Analyzed: {stats['financial_data']}")

db.close()
```

## File Structure

```
youtuber_analysis/
├── db_manager.py              # Database operations
├── youtube_search.py          # Video search with age filter
├── gemini_analyzer.py         # AI analysis with multi-stock support
├── data_importer.py           # Import YouTubers/tags
├── gemini_importer.py         # Import pre-generated JSON results
├── migrate_multi_stock.py     # Database migration script
├── test_multi_stock.py        # Test suite for multi-stock system
├── youtuber.txt               # YouTuber names + tags
├── youtube_analysis.db        # SQLite database
├── MIGRATION_REPORT.md        # Latest migration documentation
└── .claude/
    └── skills/
        └── youtube-analysis-pipeline.md  # SOP skill
```

## Customization Reference

### Modify Search Parameters (`youtube_search.py`)
- **Max results**: `--max-results` parameter (default: 10)
- **Video age filter**: `--min-age` parameter (default: 2 years)
- **Sort order**: Modify `order` parameter in `search_videos()` (line 60)

### Modify Analysis Prompt (`gemini_analyzer.py`)
- **Prompt location**: Lines 20-78 (`ANALYSIS_PROMPT`)
- **Model**: `--model` parameter (default: gemini-2.0-flash-exp)
- **Temperature**: Modify `GenerateContentConfig` (line 138)

### Add Financial Indicators
To add new analysis fields:
1. Update `ANALYSIS_PROMPT` in `gemini_analyzer.py`
2. Add column to `Youtuber_Financial_Data` table in `db_manager.py`
3. Update field mapping in `save_analysis_to_db()` method
4. Run migration script to update existing database

## Testing

```bash
# Run complete test suite
python3 test_multi_stock.py

# Test individual components
python3 db_manager.py          # Database initialization
python3 data_importer.py --help
python3 youtube_search.py --help
python3 gemini_analyzer.py --help
```

## Troubleshooting

**Issue: "Stock ticker is NULL"**
- Legacy data may have NULL stock_ticker
- New analyses will always have stock_ticker populated
- Filter with: `WHERE stock_ticker IS NOT NULL`

**Issue: "Video already analyzed"**
- System checks for existing records by video_id
- To re-analyze: Delete existing records first
- Or use different stock_ticker if adding new stock

**Issue: "Gemini returns empty array"**
- Video may not discuss any primary stocks
- Check if video is actually about stock analysis
- Review raw_json field to see Gemini's response

**Issue: "Rate limit exceeded"**
- YouTube API: Reduce max_results or spread searches
- Gemini API: Increase sleep time between calls
- Check quota usage in Google Cloud Console

## Migration History

**2025-12-25: Multi-Stock Support**
- Added `video_uuid` field
- Removed UNIQUE constraint from `video_id`
- Added composite unique constraint `(video_id, stock_ticker)`
- Updated Gemini prompt for multi-stock detection
- Backup: `youtube_analysis_backup_20251225_*.db`

## Additional Resources

- YouTube Data API: https://developers.google.com/youtube/v3
- Vertex AI Gemini: https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/overview
- SQLite Documentation: https://www.sqlite.org/docs.html
