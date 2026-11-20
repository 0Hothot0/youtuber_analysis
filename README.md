# YouTuber Stock-Call Analysis

**Do financial YouTubers' stock calls come true?**
This project collects videos from five finance YouTubers, uses Gemini to extract
which stocks each video discusses and how bullish or bearish it is, checks the
stock's actual return 1 month to 2 years later, and builds labelled datasets
for predicting whether a call will be correct. A linear soft-margin SVM is then
trained on those datasets.

> Research and educational use only. Nothing here is financial advice.

## Contents

- [Pipeline](#pipeline)
- [Repository layout](#repository-layout)
- [Datasets](#datasets)
- [Results](#results)
- [Reproducing the pipeline](#reproducing-the-pipeline)
- [Known issues](#known-issues)

## Pipeline

```
 YouTube Data API        Gemini 2.0 Flash        VADER              Yahoo Finance
       │                       │                   │                      │
 ┌─────▼──────┐   ┌────────────▼───────┐   ┌───────▼────────┐   ┌─────────▼────────┐   ┌──────────────┐
 │ 1 collect  │──▶│ 2 analyse video    │──▶│ 3 comment      │──▶│ 4 build period   │──▶│ 5 export     │
 │   videos   │   │   (1 row / stock)  │   │   sentiment    │   │   datasets       │   │   Excel      │
 └────────────┘   └────────────────────┘   └────────────────┘   └──────────────────┘   └──────┬───────┘
                         data/raw/youtube_analysis.db           data/interim/<yt>/<period>.db  │
                                                                                               ▼
                                                                     data/processed/*.xlsx ──▶ soft-margin SVM
                                                                                               results/soft_margin_svm/
```

1. **Collect** – search each YouTuber's channel for videos at least 2 years old
   (so that 2-year returns can be measured) and store their metadata.
2. **Analyse video** – Gemini watches each video and returns one record per
   *primary* stock with 17 indicators (sentiment, financial-ratio content,
   celebrity mentions, long-/short-term focus, price-trend view, ...).
3. **Comment sentiment** – average VADER score of the top 50 comments.
4. **Build period datasets** – for each YouTuber × horizon
   (1, 3, 6, 12, 24 months) compute the stock's return after the video and the
   label `class`: **1** if the call was right, **−1** otherwise.
5. **Export** – chronological 80/20 train/test split, z-score engagement counts,
   write one Excel file per YouTuber × horizon.

The labelling rule (threshold 5%):

| Video sentiment | Return over horizon | `class` |
|---|---|---|
| bullish (> 0) | ≥ +5% | 1 |
| neutral (= 0) | between −5% and +5% | 1 |
| bearish (< 0) | ≤ −5% | 1 |
| anything else | | −1 |

See [docs/methodology.md](docs/methodology.md) for details.

## Repository layout

```
youtuber_analysis/
├── config/
│   ├── youtubers.yaml          # the 5 YouTubers (key, name, channel title)
│   ├── settings.yaml           # horizons, 5% threshold, split, features
│   └── search_tags.txt         # search keywords
├── src/youtuber_analysis/      # Python package
│   ├── config.py               # paths + config loading
│   ├── db.py                   # SQLite schema and helpers
│   ├── collect/youtube.py      # YouTube Data API client
│   ├── analyze/gemini.py       # Gemini video analysis
│   ├── analyze/sentiment.py    # VADER comment sentiment
│   ├── market/prices.py        # Yahoo Finance prices and returns
│   ├── market/labeling.py      # class label rule
│   ├── dataset/build.py        # per-YouTuber, per-horizon databases
│   └── dataset/export.py       # train/test split, scaling, Excel
├── scripts/                    # one script per pipeline step, run in order
│   ├── 00_init_db.py
│   ├── 01_collect_videos.py
│   ├── 02_analyze_videos.py
│   ├── 03_comment_sentiment.py
│   ├── 04_build_period_datasets.py
│   └── 05_export_excel.py
├── data/
│   ├── raw/                    # master database (not in git)
│   ├── interim/                # per-period databases (not in git)
│   └── processed/              # 25 model-ready Excel files  ← in git
├── results/
│   └── soft_margin_svm/        # SVM workbooks per YouTuber and horizon  ← in git
├── docs/
│   ├── methodology.md
│   └── data_dictionary.md
└── tests/
```

## Datasets

Five YouTubers, videos published Jul 2022 – Jan 2024. One record = one
(video, stock) pair, so a video discussing three stocks gives three records.

| Key | YouTuber | Records | Videos | Unique stocks | Published |
|---|---|---:|---:|---:|---|
| `joseph` | Let's Talk Money! with Joseph Hogue, CFA | 466 | 92 | 247 | Dec 2022 – Jan 2024 |
| `tom_nash` | Tom Nash | 123 | 77 | 32 | Mar 2023 – Jan 2024 |
| `fin_tek` | Fin Tek | 114 | 91 | 35 | Nov 2023 – Jan 2024 |
| `henry` | Invest with Henry | 251 | 76 | 43 | Apr 2023 – Jan 2024 |
| `paul` | Paul Thomas Investing | 66 | 40 | 31 | Jul 2022 – Jan 2024 |
| | **Total** | **1,020** | **376** | | |

**`data/processed/<youtuber>_<horizon>.xlsx`** (25 files) – sheets
`Training_Data` (earliest 80%) and `Test_Data` (latest 20%), each with 12
features and the target `class`. Column definitions:
[docs/data_dictionary.md](docs/data_dictionary.md).

**`results/soft_margin_svm/<youtuber>/<horizon>.xlsx`** – the trained linear
soft-margin SVM for each dataset (`all/` pools Joseph, Tom Nash, Fin Tek and
Henry). Sheet `train` holds the fitted weights `w`, bias `b`, slack `ksi` and
objective value; sheet `test` holds each test row's decision value,
predicted class and the resulting accuracy. There are no SVM results for Paul
Thomas; his `comment_sentiment` column is all zeros (never collected).

## Results

### Share of correct calls (`class = 1`)

| YouTuber | 1 month | 3 months | 6 months | 1 year | 2 years |
|---|---:|---:|---:|---:|---:|
| Joseph Hogue | 31.1% | 30.0% | 38.6% | 36.3% | 42.7% |
| Tom Nash ¹ | 41.5% | 35.8% | 37.4% | 45.5% | 55.3% |
| Fin Tek | 57.0% | 49.1% | 44.7% | 64.0% | 58.8% |
| Invest with Henry | 39.0% | 34.7% | 32.3% | 34.3% | 29.1% |
| Paul Thomas | 25.8% | 18.2% | 18.2% | 15.2% | 24.2% |

¹ Recomputed with the labelling rule. The shipped Tom Nash 3-month and 2-year
files use a different label; see [Known issues](#known-issues).

### Soft-margin SVM test accuracy

| Dataset | 1 month | 3 months | 6 months | 1 year | 2 years |
|---|---:|---:|---:|---:|---:|
| Joseph Hogue | 68.1% | 67.0% | 58.1% | 72.3% | 84.0% |
| Tom Nash ¹ | 36.0% | 52.0% | 68.0% | 76.0% | 92.0% |
| Fin Tek | 52.2% | 52.2% | 39.1% | 78.3% | 73.9% |
| Invest with Henry | 72.5% | 76.0% | 76.0% | 84.3% | 88.2% |
| All four pooled ¹ | 65.3% | 60.6% | 64.6% | 67.4% | 77.7% |

¹ Tom Nash 3 months / 2 years (and the pooled sets that include them) were
trained on the mislabelled files.

## Reproducing the pipeline

Requirements: Python 3.10+, a YouTube Data API v3 key and, for step 2, a
Google Cloud project with Vertex AI enabled.

```bash
git clone https://github.com/0Hothot0/youtuber_analysis.git
cd youtuber_analysis
pip install -e ".[dev]"
cp .env.example .env        # fill in YOUTUBE_API_KEY and GOOGLE_CLOUD_PROJECT
```

```bash
python scripts/00_init_db.py                       # create data/raw/youtube_analysis.db
python scripts/01_collect_videos.py --youtuber all # search videos (uses API quota)
python scripts/02_analyze_videos.py --limit 50     # Gemini analysis
python scripts/03_comment_sentiment.py             # VADER comment sentiment
python scripts/04_build_period_datasets.py         # returns + labels, 5 YouTubers x 5 horizons
python scripts/05_export_excel.py                  # data/processed/*.xlsx
```

Every script accepts `--help`. Steps 4 and 5 take `--youtuber <key|all>` and
`--period <1month|3months|6months|1year|2years|all>`.

Run the tests with `pytest`.

**API quota.** YouTube allows 10,000 units/day; a search costs ~100 units and a
comment page ~1 unit. Gemini calls are spaced 2 s apart and retried up to 3
times.

## Known issues

- **Tom Nash 3-month and 2-year labels.** In these two datasets `class` was
  computed as `1 if return > 0 else -1` instead of the sentiment-vs-return rule
  above (all 123 rows match that rule exactly). This inflates the 2-year share
  of correct calls from 55.3% to 94.3%. The returns themselves are correct, so
  the labels can be recomputed without re-downloading prices.
- **Comment sentiment differs slightly across horizons** for some videos,
  because it was originally fetched separately for each horizon on different
  days. The pipeline now computes it once on the master database (step 3) so
  every horizon shares the same value.

## Acknowledgements

YouTube Data API v3 · Google Vertex AI Gemini · VADER Sentiment · Yahoo Finance (yfinance)
