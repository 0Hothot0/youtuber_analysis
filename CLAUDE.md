# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube video search tool that uses the YouTube Data API v3 to search for videos by keyword and export detailed metadata in both JSON and CSV formats. The primary use case is analyzing stock-related videos but works with any search keyword.

## Architecture

The codebase consists of a single-file CLI application with a class-based design:

- **YouTubeSearcher class**: Encapsulates all YouTube API interactions
  - `search_videos()`: Uses `search.list` API to find video IDs by keyword (relevance-sorted)
  - `get_video_details()`: Uses `videos.list` API to fetch full metadata (statistics, content details)
  - `save_results()`: Outputs both JSON and CSV to `output/` directory with timestamped filenames

The tool makes two separate API calls because YouTube's search endpoint doesn't return complete statistics like view counts and duration.

## Environment Setup

### Prerequisites
- Python 3.12+
- YouTube Data API v3 Key from Google Cloud Console

### Installation
```bash
# Install dependencies (may need --break-system-packages on Debian/Ubuntu)
python3 -m pip install -r requirements.txt --user --break-system-packages

# Configure API key
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY
```

## Running the Tool

```bash
python3 youtube_search.py "search keyword"
```

Output files are saved to `output/{keyword}_{timestamp}.{json,csv}`

## API Quota Considerations

YouTube Data API v3 has a daily quota limit (default 10,000 units). Each search consumes ~100 units:
- `search.list`: ~100 units
- `videos.list`: ~1 unit

## Customization Reference

Common modifications (see README.md FAQ for line numbers):
- **Max results**: Modify `max_results` parameter in `search_videos()` call (line 226)
- **Sort order**: Change `order` parameter in search request (line 52). Options: `relevance`, `date`, `viewCount`, `rating`, `title`
- **Output fields**: Modify `video_info` dict (lines 106-121) and `columns_order` (lines 165-172)

## Data Output Schema

Both JSON and CSV contain these fields per video:
- video_id, title, url
- channel_name, channel_id
- view_count, like_count, comment_count
- published_at (formatted as YYYY-MM-DD HH:MM:SS)
- duration (ISO 8601 duration parsed to readable format)
- thumbnail_default, thumbnail_medium, thumbnail_high
- description (full text)
