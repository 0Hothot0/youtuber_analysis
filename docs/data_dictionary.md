# Data dictionary

## Model-ready Excel files

`data/processed/<youtuber>_<period>.xlsx`, sheets `Training_Data` and `Test_Data`.

| # | Column | Type | Range | Meaning |
|---|---|---|---|---|
| 1 | `like_number` | float | z-score | Video likes, standardised on the training split |
| 2 | `comment_number` | float | z-score | Video comment count, standardised |
| 3 | `view_number` | float | z-score | Video views, standardised |
| 4 | `text_type` | int | 0 / 1 | 1 = functional (analysis, data, facts); 0 = social-bond (opinion) |
| 5 | `video_sentiment` | float | −1 … 1 | Video's sentiment toward the stock (Gemini) |
| 6 | `comment_sentiment` | float | −1 … 1 | Mean VADER compound score of top comments |
| 7 | `financial_ratio` | float | 0 … 1 | Share of financial content (charts, numbers, terms) |
| 8 | `celebrity` | int | 0 / 1 | Mentions famous investors or CEOs |
| 9 | `relevancy` | float | 0 … 1 | Relevance of the content to the stock |
| 10 | `long_term_competitiveness` | int | 0 / 1 | Discusses long-term growth or industry trends |
| 11 | `short_term_focus` | int | 0 / 1 | Focuses on recent news or short-term catalysts |
| 12 | `stock_price_growth_trend` | float | −1 … 1 | Described price trend: −1 declining, 1 growing |
| | **`class`** | int | 1 / −1 | **Target.** 1 = call was correct, −1 = incorrect (see methodology §5) |

## Database (`Youtuber_Financial_Data` table)

One row per (video, primary stock). Besides the columns above (stored
unstandardised), it contains:

| Column | Type | Meaning |
|---|---|---|
| `id` | int | Row ID |
| `video_uuid` | text | Shared by all stocks of the same video |
| `video_id` | text | YouTube video ID |
| `stock_ticker` | text | Stock symbol, e.g. `TSLA` |
| `published_time` | text | Video publish time, `YYYY-MM-DD HH:MM:SS` (UTC) |
| `ceo_leadership_style` | int 0/1 | Mentions CEO management style or vision |
| `earnings_expectation_gap` | float −1…1 | Earnings vs expectations: −1 below, 1 above |
| `market_demand` | float −1…1 | Described demand: −1 weak, 1 strong |
| `market_capitalization` | int 0/1 | Mentions market cap |
| `target_price` | int 0/1 | Mentions an analyst price target |
| `financial_health` | float −1…1 | Described financial health: −1 weak, 1 strong |
| `valuation` | float −1…1 | −1 overvalued, 0 fair, 1 undervalued |
| `policy_impact` | float −1…1 | Effect of policy/regulation: −1 negative, 1 positive |
| `raw_json` | text | Gemini's raw JSON response for the video |
| `return_rate` | float | Stock return over the horizon (0.05 = 5%) |
| `during` | int | Days between publish date and evaluation date |
| `youtuber` | text | Channel title |
| `created_at`, `updated_at` | text | Row timestamps |

Gemini returns 0 for any indicator the video does not mention.

### Other tables

| Table | Content |
|---|---|
| `videos` | YouTube metadata: title, channel, publish time, views, likes, comments, duration, thumbnails, the search query that found it |
| `youtubers` | Channel titles (linked from `videos.youtuber_id`) |
| `search_tags` | Search keywords from `config/search_tags.txt` |

## SVM result workbooks

`results/soft_margin_svm/<dataset>/<period>.xlsx`, where `<dataset>` is
`joseph`, `tom_nash`, `fin_tek`, `henry` or `all`.

| Sheet | Content |
|---|---|
| `train` | Fitted weights `w` (12 values, feature order as above), `w+`/`w−`, bias `b`, objective `obj`, `sum_ksi`; per-row slack `ksi`, decision value, predicted class, training accuracy |
| `test` | Test rows with decision value `predict_value`, `predict_class`, `correct`, and the test accuracy and confusion counts |
