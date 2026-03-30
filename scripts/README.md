# Scripts Directory

This directory contains the main scripts for the YouTuber Analysis project.

## Core Scripts

### Comment Sentiment Analysis
- **analyze_comments_free.py** - Analyze comment sentiment using VADER (free, no API costs)
  - Supports: Joseph, Tom Nash, Fin Tek, Henry (excludes Paul per requirements)
  - Usage: `python3 scripts/analyze_comments_free.py --youtuber all`

### Database Creation
- **create_multi_period_joseph.py** - Create Joseph Hogue's multi-period databases
- **create_multi_period_tom_nash.py** - Create Tom Nash's multi-period databases
- **create_multi_period_fintek.py** - Create Fin Tek's multi-period databases
- **create_multi_period_henry.py** - Create Invest with Henry's multi-period databases
- **create_multi_period_paul.py** - Create Paul Thomas's multi-period databases

Each creates 5 time period databases (1month, 3months, 6months, 1year, 2years) with recalculated return rates and class labels.

### Data Export
- **export_all_5periods_complete.py** - Export all YouTubers' data to Excel with time series split
  - Creates 25 Excel files (5 YouTubers × 5 periods)
  - Includes Training_Data and Test_Data sheets (80/20 split, no temporal overlap)
  - 13 features including comment_sentiment and class

### Database Updates
- **update_2year_return.py** - Update 2-year return rates in database
- **update_3month_return.py** - Update 3-month return rates in database
- **update_return_class.py** - Update classification labels based on return rates
- **update_prediction_accuracy.py** - Calculate prediction accuracy metrics

### Automation
- **run_pipeline.py** - Automated pipeline for complete analysis workflow
- **auto_report.py** - Generate progress reports

## Subdirectories

### deprecated/
Contains experimental or outdated scripts that are no longer used in the main workflow but kept for reference.

### utilities/
Contains one-time utility scripts for database cleanup, verification, and special operations.
