# YouTuber Financial Analysis System

A comprehensive system for analyzing financial YouTubers' stock recommendations and predicting their accuracy using AI-powered video analysis and sentiment analysis.

## 🎯 Project Overview

This system analyzes 5 financial YouTubers' videos to extract stock recommendations, evaluate comment sentiment, and predict recommendation accuracy over multiple time periods (1 month, 3 months, 6 months, 1 year, 2 years).

**Analyzed YouTubers:**
- Joseph Hogue (Let's Talk Money! with Joseph Hogue, CFA)
- Tom Nash
- Fin Tek
- Invest with Henry
- Paul Thomas Investing

## ✨ Key Features

### 1. AI-Powered Video Analysis
- **Gemini 2.0 Flash** integration for multi-stock detection per video
- Extracts 17 financial indicators including:
  - Video sentiment, financial ratios, celebrity mentions
  - Relevancy, long-term competitiveness, short-term focus
  - Stock price growth trend
- Supports multi-stock analysis (one video can discuss multiple stocks)

### 2. Comment Sentiment Analysis
- **VADER** sentiment analysis (free, no API costs)
- Analyzes top 50 comments per video
- Returns sentiment scores (-1 to +1)
- Processed 1,327+ videos successfully

### 3. Multi-Period Stock Return Tracking
- Calculates actual stock returns over 5 time periods
- Integrates with Yahoo Finance for historical prices
- Binary classification: prediction correct (1) or incorrect (-1)
- Threshold: ±5% for neutral predictions

### 4. Time Series Data Export
- **25 Excel files** (5 YouTubers × 5 periods)
- **80/20 train/test split** with no temporal overlap
- **12 input features + 1 target variable (class)**
  - Engagement metrics (likes, comments, views)
  - Sentiment scores (video + comments)
  - Financial indicators
- Z-score normalization for numerical features

## 📊 Dataset Statistics

| YouTuber | Total Videos | Unique Stocks | Data Range |
|----------|--------------|---------------|------------|
| Joseph Hogue | 466 | 247 | Dec 2022 - Jan 2024 |
| Tom Nash | 123 | 32 | Mar 2023 - Jan 2024 |
| Fin Tek | 114 | 35 | Nov 2023 - Jan 2024 |
| Invest with Henry | 251 | 43 | Apr 2023 - Jan 2024 |
| Paul Thomas | 66 | 31 | Jul 2022 - Jan 2024 |

**Total:** 1,020 videos analyzing 388 unique stocks

## 🛠️ Installation

### Prerequisites
- Python 3.12+
- YouTube Data API v3 Key
- Google Cloud Project with Vertex AI (optional, for Gemini analysis)

### Setup

```bash
# Clone repository
git clone https://github.com/0Hothot0/youtuber_analysis.git
cd youtuber_analysis

# Install dependencies
pip install -r requirements.txt --user --break-system-packages

# Configure environment
cp .env.example .env
# Edit .env and add:
#   YOUTUBE_API_KEY=your_youtube_key
#   GOOGLE_CLOUD_PROJECT=your_gcp_project (optional)
#   GOOGLE_CLOUD_LOCATION=us-central1 (optional)
```

## 🚀 Usage

### Comment Sentiment Analysis (Free)

```bash
# Analyze all YouTubers
python3 scripts/analyze_comments_free.py --youtuber all

# Analyze specific YouTuber
python3 scripts/analyze_comments_free.py --youtuber joseph --period 1year

# Test mode (3 videos)
python3 scripts/analyze_comments_free.py --youtuber joseph --limit 3
```

### Create Multi-Period Databases

```bash
# Create databases for specific YouTuber
python3 scripts/create_multi_period_joseph.py
python3 scripts/create_multi_period_tom_nash.py
python3 scripts/create_multi_period_fintek.py
python3 scripts/create_multi_period_henry.py
python3 scripts/create_multi_period_paul.py
```

### Export to Excel

```bash
# Export all YouTubers with time series split
python3 scripts/export_all_5periods_complete.py
# Output: exports/all_5periods_timeseries/*.xlsx (25 files)
```

## 📁 Project Structure

```
youtuber_analysis/
├── core/                           # Core modules
│   ├── db_manager.py              # Database operations
│   ├── youtube_search.py          # YouTube API integration
│   ├── gemini_analyzer.py         # Gemini AI video analysis
│   ├── stock_price_fetcher.py     # Yahoo Finance integration
│   └── comment_sentiment_analyzer.py
│
├── scripts/                        # Main scripts
│   ├── analyze_comments_free.py   # VADER sentiment analysis
│   ├── create_multi_period_*.py   # Database creation (5 YouTubers)
│   ├── export_all_5periods_complete.py  # Excel export
│   ├── update_*.py                # Database update utilities
│   ├── deprecated/                # Experimental scripts
│   └── utilities/                 # One-time utility scripts
│
├── docs/                          # Technical documentation
├── exports/                       # Excel output files (gitignored)
├── {youtuber}/                    # YouTuber databases (gitignored)
│   └── youtube_analysis_{period}_single_{name}.db
│
├── CLAUDE.md                      # Claude Code instructions
├── README.md                      # This file
├── requirements.txt               # Python dependencies
└── .gitignore                     # Git ignore rules
```

## 📈 Data Schema

### Excel Output Format

Each Excel file contains 2 sheets:
- **Training_Data** (80% - earlier videos)
- **Test_Data** (20% - later videos)

**12 Input Features:**
1. `like_number` - Video likes (standardized)
2. `comment_number` - Video comments (standardized)
3. `view_number` - Video views (standardized)
4. `text_type` - Content type classification
5. `video_sentiment` - AI-analyzed video sentiment (-1 to 1)
6. `comment_sentiment` - VADER sentiment score (-1 to 1)
7. `financial_ratio` - Financial metrics discussion
8. `celebrity` - Celebrity/influencer mentions
9. `relevancy` - Stock relevance to discussion
10. `long_term_competitiveness` - Long-term outlook
11. `short_term_focus` - Short-term focus indicator
12. `stock_price_growth_trend` - Price trend analysis

**Target Variable:**
- `class` - Prediction accuracy (1=correct, -1=incorrect)

### Database Schema

**Primary Table:** `Youtuber_Financial_Data`
- 28 fields including video metadata, AI analysis, stock data
- Composite unique key: `(video_id, stock_ticker)`
- `video_uuid` for grouping multi-stock videos

## 🎓 Research Use Cases

This dataset is suitable for:
- **Machine Learning**: Binary classification of stock recommendation accuracy
- **Sentiment Analysis**: Correlation between sentiment and stock performance
- **Time Series Analysis**: Performance prediction across different periods
- **Natural Language Processing**: Video content analysis
- **Financial Analysis**: YouTuber recommendation patterns

## 📊 Key Findings

### Prediction Accuracy by Period

| YouTuber | 1 Month | 3 Months | 6 Months | 1 Year | 2 Years |
|----------|---------|----------|----------|--------|---------|
| Joseph Hogue | 31.1% | 30.0% | 38.6% | 36.3% | **42.7%** |
| Tom Nash | 41.5% | 55.3% | 37.4% | 45.5% | **94.3%** |
| Fin Tek | 57.0% | 49.1% | 44.7% | **64.0%** | 58.8% |
| Invest with Henry | 39.0% | 34.7% | 32.3% | 34.3% | 29.1% |
| Paul Thomas | 25.8% | 18.2% | 18.2% | 15.2% | 24.2% |

**Notable Insights:**
- Tom Nash shows exceptional long-term accuracy (94.3% for 2-year predictions)
- Fin Tek performs best at 1-year timeframe (64.0%)
- Short-term predictions are generally less reliable across all YouTubers

### Most Recommended Stocks

**Joseph Hogue:** TSLA (15), AAPL (12), SOFI (11)
**Tom Nash:** TSLA (39), PLTR (35), NVDA (8)
**Fin Tek:** SOFI (8), SNOW (8), CRWD (8)
**Invest with Henry:** TSLA (37), AAPL (26), SPY (23)
**Paul Thomas:** NIO (8), PSNY (7), ILUS (7)

## 🔧 API Quota Considerations

**YouTube Data API v3:**
- Daily limit: 10,000 units (default)
- `search.list`: ~100 units per call
- Recommended delay: 0.5 seconds between requests

**Gemini API (optional):**
- Uses Gemini 3.1 Pro (experimental)
- Rate limits apply - use delays between calls
- Alternative: VADER for free sentiment analysis

## 📝 Documentation

Detailed documentation available in `/docs`:
- Database cleanup procedures
- Comment sentiment analysis guides
- Excel export methodologies
- YouTuber-specific reports

## 🤝 Contributing

This is a research project. For questions or collaboration:
1. Open an issue on GitHub
2. Review existing documentation in `/docs`
3. Check CLAUDE.md for project instructions

## ⚠️ Disclaimer

This project is for research and educational purposes only. Stock recommendations from YouTubers should not be considered financial advice. Past performance does not guarantee future results.

## 📜 License

This project is for academic and research use.

## 🙏 Acknowledgments

- YouTube Data API v3 for video metadata
- Google Vertex AI Gemini for video analysis
- VADER Sentiment for comment analysis
- Yahoo Finance for stock price data
- Claude Code (Anthropic) for development assistance

---

**Last Updated:** March 2026
**Repository:** https://github.com/0Hothot0/youtuber_analysis
**Branch:** dev
