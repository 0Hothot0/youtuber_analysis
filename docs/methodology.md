# Methodology

## 1. Research question

Can the content of a financial YouTube video predict whether the stock call it
makes will turn out to be correct? A call is "correct" when the direction of
the video's sentiment toward a stock matches the stock's realised return over a
given horizon.

## 2. Sample

* **YouTubers (5):** Let's Talk Money! with Joseph Hogue, CFA; Tom Nash; Fin Tek;
  Invest with Henry; Paul Thomas Investing (`config/youtubers.yaml`).
* **Videos:** found with the YouTube Data API v3 `search.list` endpoint, querying
  `"<YouTuber name> <keyword>"` and keeping only videos published at least two
  years before the search date, so that a 2-year return is observable.
* **Unit of analysis:** a (video, stock) pair. A video discussing several stocks
  produces several records sharing one `video_uuid`. The pair
  `(video_id, stock_ticker)` is unique.
* **Final sample:** 1,020 records from 376 videos, published Jul 2022 – Jan 2024.

## 3. Video content features (Gemini)

Each video URL is passed to Gemini 2.0 Flash on Vertex AI (temperature 0.2, up to
3 retries with exponential backoff). The prompt (`src/youtuber_analysis/analyze/gemini.py`)
asks the model to:

1. identify only **primary** stocks – discussed at length, analysed with data or
   charts, or part of the video's main topic – and ignore passing mentions;
2. return a JSON array with one object per primary stock;
3. score 17 indicators per stock, using 0 for anything not mentioned (no inference).

The full indicator list and value ranges are in [data_dictionary.md](data_dictionary.md).
Engagement counts (`like_number`, `comment_number`, `view_number`) come from the
YouTube API at collection time.

## 4. Comment sentiment (VADER)

The top 50 comments (YouTube `relevance` order) are fetched. Comments are split
into lines, and the first 50 non-empty lines are scored with VADER. The mean
compound score (−1 to 1) is stored as `comment_sentiment`. Videos with no
comments score 0. VADER was chosen over an LLM because it is free, local and
deterministic.

## 5. Returns and labels

For a horizon of *m* months (1, 3, 6, 12, 24):

* `start` = video publish date, `end` = `start + m months`;
* price on each date = closing price on the nearest trading day within ±7 days
  (Yahoo Finance via `yfinance`); records with no price, or whose `end` is in the
  future, are dropped;
* `return_rate = (P_end − P_start) / P_start`;
* `during` = number of days between `start` and `end`;
* `class` is assigned with a 5% threshold:

| `video_sentiment` | `return_rate` | `class` |
|---|---|---|
| > 0 (bullish) | ≥ 0.05 | 1 |
| = 0 (neutral) | −0.05 < r < 0.05 | 1 |
| < 0 (bearish) | ≤ −0.05 | 1 |
| otherwise | | −1 |

This produces 25 datasets (5 YouTubers × 5 horizons), stored as
`data/interim/<youtuber>/<period>.db`.

## 6. Model-ready datasets

`scripts/05_export_excel.py` turns each period database into
`data/processed/<youtuber>_<period>.xlsx`:

1. **Features:** 12 inputs (`like_number`, `comment_number`, `view_number`,
   `text_type`, `video_sentiment`, `comment_sentiment`, `financial_ratio`,
   `celebrity`, `relevancy`, `long_term_competitiveness`, `short_term_focus`,
   `stock_price_growth_trend`) and the target `class`.
2. **Chronological split:** records are sorted by publish time. The earliest 80%
   form the training set and the latest 20% the test set, so no test video
   predates a training video (no look-ahead).
3. **Shuffle** rows within each split (seed 42).
4. **Standardise** `like_number`, `comment_number` and `view_number` with a z-score
   whose mean and standard deviation are fitted on the training split only.

## 7. Classifier

A linear soft-margin support vector machine is fitted to each training set and
evaluated on the corresponding test set. The workbooks in
`results/soft_margin_svm/` contain the fitted weight vector `w` (one weight per
feature), bias `b`, slack variables `ksi`, the objective value, each test row's
decision value and predicted class, and the test accuracy. Datasets: each of
Joseph Hogue, Tom Nash, Fin Tek and Invest with Henry separately, plus the four
pooled (`all/`).

## 8. Reproducibility notes

* Gemini output is not fully deterministic, even at temperature 0.2.
* Yahoo Finance adjusts historical prices for splits and dividends, so
  recomputed returns can differ slightly from the stored ones.
* Engagement counts and comments change over time; the stored values reflect the
  collection date (Dec 2025 – Mar 2026).
* Known data issues are listed in the README.
