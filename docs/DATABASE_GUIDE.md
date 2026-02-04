# 資料庫使用指南

## 已建立的檔案結構

```
youtuber_analysis/
├── db_manager.py              # 資料庫管理模組
├── data_importer.py           # youtuber.txt 匯入工具
├── gemini_importer.py         # Gemini 分析結果匯入工具
├── youtube_search.py          # YouTube 搜尋工具 (原有)
├── youtube_analysis.db        # SQLite 資料庫 (已初始化)
├── youtuber.txt              # YouTuber 和標籤來源檔案
├── data/
│   ├── youtubers.csv         # YouTuber 清單 CSV
│   └── search_tags.csv       # 搜尋標籤 CSV
└── output/                    # YouTube 搜尋結果輸出目錄
```

## 資料庫結構

### 資料表概覽
- **youtubers** (10 筆) - YouTuber 清單
- **search_tags** (41 筆) - 搜尋標籤
- **videos** (0 筆) - YouTube 影片資料
- **Youtuber_Financial_Data** (0 筆) - Gemini 分析結果

## 使用方式

### 1. 初始化資料庫 (已完成)
```bash
python3 data_importer.py
```
✓ 已執行完成：10 個 YouTuber 和 41 個標籤已匯入

### 2. 搜尋 YouTube 影片並存入資料庫

目前 `youtube_search.py` 只支援 JSON/CSV 輸出，需要手動將結果匯入資料庫。

**方法 A: 使用現有腳本搜尋並手動匯入**
```bash
# 搜尋影片
python3 youtube_search.py "Invest with Henry stock analysis"

# 手動匯入 (需要寫額外的轉換腳本)
```

**方法 B: 修改 youtube_search.py 直接存入資料庫**
```python
# 在 youtube_search.py 中添加資料庫儲存功能
from db_manager import DatabaseManager

# 在 save_results 方法後添加:
db = DatabaseManager()
db.connect()
for video in videos_data:
    video['youtuber_id'] = 1  # 根據實際情況設定
    db.insert_video(video)
db.close()
```

### 3. 匯入 Gemini 分析結果

#### JSON 格式範例

**單筆資料:**
```json
{
  "video_id": "CEJk8NWm5pw",
  "stock_ticker": "AAPL",
  "like_number": 932,
  "comment_number": 217,
  "view_number": 25039,
  "text_type": 1,
  "video_sentiment": 0.8,
  "comment_sentiment": 0.6,
  "financial_ratio": 0.9,
  "celebrity": 0,
  "relevancy": 0.95,
  "published_time": "2025-12-08 23:00:17",
  "long_term_competitiveness": 1,
  "short_term_focus": 1,
  "ceo_leadership_style": 0,
  "earnings_expectation_gap": 0.5,
  "stock_price_growth_trend": 0.7,
  "market_demand": 0.8,
  "market_capitalization": 1,
  "target_price": 1,
  "financial_health": 0.9,
  "valuation": -0.2,
  "policy_impact": 0.3
}
```

**批次資料:**
```json
[
  {
    "video_id": "CEJk8NWm5pw",
    ...
  },
  {
    "video_id": "ylm2vDQka68",
    ...
  }
]
```

#### 匯入指令
```bash
# 單筆匯入
python3 gemini_importer.py gemini_single.json

# 批次匯入
python3 gemini_importer.py gemini_batch.json
```

## 資料庫查詢範例

### 使用 Python 查詢

```python
from db_manager import DatabaseManager

db = DatabaseManager()
db.connect()

# 取得所有 YouTuber
youtubers = db.get_all_youtubers()
for yt in youtubers:
    print(f"{yt['id']}: {yt['name']}")

# 取得特定 YouTuber 的影片
videos = db.get_videos_by_youtuber(youtuber_id=1)

# 取得影片的財務分析資料
financial_data = db.get_financial_data_by_video(video_id="CEJk8NWm5pw")

# 統計資訊
stats = db.get_statistics()
print(stats)

db.close()
```

### 使用 SQL 查詢 (需要 sqlite3)

```bash
sqlite3 youtube_analysis.db

# 查看所有 YouTuber
SELECT * FROM youtubers;

# 查看搜尋標籤
SELECT * FROM search_tags LIMIT 10;

# 查詢影片及其所屬 YouTuber
SELECT v.title, y.name
FROM videos v
JOIN youtubers y ON v.youtuber_id = y.id;

# 查詢影片的財務分析
SELECT f.stock_ticker, f.video_sentiment, f.valuation, v.title
FROM Youtuber_Financial_Data f
JOIN videos v ON f.video_id = v.video_id;
```

## 資料欄位說明

### Youtuber_Financial_Data 欄位

| 欄位 | 類型 | 範圍 | 說明 |
|------|------|------|------|
| video_id | TEXT | - | YouTube 影片 ID (必填) |
| stock_ticker | TEXT | - | 股票代碼 |
| like_number | INTEGER | - | 按讚數 |
| comment_number | INTEGER | - | 評論數 |
| view_number | INTEGER | - | 觀看數 |
| text_type | INTEGER | 0/1 | 0=社會聯繫導向, 1=功能導向 |
| video_sentiment | REAL | -1~1 | 影片情感分數 |
| comment_sentiment | REAL | -1~1 | 評論情感分數 |
| financial_ratio | REAL | 0~1 | 財務相關元素比例 |
| celebrity | INTEGER | 0/1 | 是否包含名人 |
| relevancy | REAL | 0~1 | 與核心訊息的相關性 |
| published_time | TEXT | - | 發布時間 |
| long_term_competitiveness | INTEGER | 0/1 | 是否提及長期競爭力 |
| short_term_focus | INTEGER | 0/1 | 是否專注短期市場 |
| ceo_leadership_style | INTEGER | 0/1 | 是否提及 CEO 管理風格 |
| earnings_expectation_gap | REAL | -1~1 | 收益與預期差距 |
| stock_price_growth_trend | REAL | -1~1 | 股價增長趨勢 |
| market_demand | REAL | -1~1 | 市場需求水準 |
| market_capitalization | INTEGER | 0/1 | 是否提及市值 |
| target_price | INTEGER | 0/1 | 是否提及目標價 |
| financial_health | REAL | -1~1 | 財務健康度 |
| valuation | REAL | -1~1 | 估值評估 (負=高估, 正=低估) |
| policy_impact | REAL | -1~1 | 政策影響評估 |
| raw_json | TEXT | - | 原始 Gemini JSON 回應 |

## 下一步

1. **修改 youtube_search.py** 添加資料庫儲存功能
2. **整合 Gemini API** 自動分析影片並匯入結果
3. **建立資料分析腳本** 統計和視覺化財務資料
4. **建立 Web 介面** 查詢和管理資料

## 檔案說明

- **db_manager.py** - 提供完整的 CRUD 操作，可直接在其他腳本中 import 使用
- **data_importer.py** - 一次性執行的初始化工具
- **gemini_importer.py** - 可重複執行，支援單筆/批次匯入
