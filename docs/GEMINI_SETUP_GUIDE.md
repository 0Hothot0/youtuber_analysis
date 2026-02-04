# Gemini Video Analyzer 設定指南

## 已完成的設定

✅ 1. 安裝 google-genai 套件 (v1.55.0)
✅ 2. 更新 requirements.txt
✅ 3. 更新 .env 和 .env.example 檔案
✅ 4. 建立 gemini_analyzer.py 完整功能腳本
✅ 5. 安裝並設定 gcloud CLI
✅ 6. 設定 Google Cloud 專案: carbon-scene-480709-t1

## 需要完成的步驟

### 步驟 1: 驗證 Google Cloud 帳戶

為了使用 Vertex AI Gemini API，您需要完成帳戶驗證。請執行以下命令：

```bash
# 方法 1: 使用瀏覽器進行使用者驗證（推薦用於開發測試）
/home/eliza/google-cloud-sdk/bin/gcloud auth login

# 設定 Application Default Credentials
/home/eliza/google-cloud-sdk/bin/gcloud auth application-default login
```

這會開啟瀏覽器視窗，請使用您的 Google 帳戶登入。

**或者**

```bash
# 方法 2: 使用服務帳戶金鑰（推薦用於生產環境）
# 1. 在 Google Cloud Console 建立服務帳戶
# 2. 下載 JSON 金鑰檔案
# 3. 設定環境變數
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
```

### 步驟 2: 啟用 Vertex AI API

確保您的專案已啟用 Vertex AI API：

```bash
# 啟用 Vertex AI API
/home/eliza/google-cloud-sdk/bin/gcloud services enable aiplatform.googleapis.com --project=carbon-scene-480709-t1

# 驗證 API 是否已啟用
/home/eliza/google-cloud-sdk/bin/gcloud services list --enabled --filter="aiplatform.googleapis.com" --project=carbon-scene-480709-t1
```

### 步驟 3: 測試 Gemini Analyzer

完成驗證後，測試分析器：

```bash
# 進入專案目錄
cd /home/eliza/Developer/youtuber_analysis

# 方法 1: 分析單一影片（使用資料庫中的影片 ID）
python3 gemini_analyzer.py --video-id "0lTM2lE1Oww"

# 方法 2: 批次分析未處理的影片（最多 3 個用於測試）
python3 gemini_analyzer.py --batch --limit 3

# 方法 3: 分析特定 YouTuber 的影片
python3 gemini_analyzer.py --batch --youtuber "Invest with Henry" --limit 5
```

## 使用說明

### gemini_analyzer.py 命令列參數

| 參數 | 說明 | 範例 |
|------|------|------|
| `--video-id` | 分析指定的影片 ID | `--video-id "CEJk8NWm5pw"` |
| `--batch` | 批次分析未處理的影片 | `--batch` |
| `--youtuber` | 批次分析時指定特定 YouTuber | `--youtuber "Tom Nash"` |
| `--limit` | 批次分析的數量限制（預設 10） | `--limit 5` |
| `--model` | 使用的 Gemini 模型（預設 gemini-2.0-flash-exp） | `--model "gemini-2.0-flash-exp"` |

### 分析流程

1. **讀取資料庫**: 從 `videos` 資料表取得影片資訊
2. **呼叫 Gemini API**: 傳送 YouTube URL 給 Vertex AI Gemini 進行分析
3. **解析回應**: 將 Gemini 回傳的 JSON 轉換為結構化資料
4. **儲存結果**: 將 23 個財務分析欄位儲存到 `Youtuber_Financial_Data` 資料表

### 分析的財務指標（23 個欄位）

1. **stock_ticker**: 股票代碼（如 AAPL, TSLA）
2. **text_type**: 1=功能導向, 0=社會聯繫導向
3. **video_sentiment**: 影片情感 (-1 到 1)
4. **financial_ratio**: 財務相關元素比例 (0 到 1)
5. **celebrity**: 1=提及名人, 0=沒有
6. **relevancy**: 核心訊息相關性 (0 到 1)
7. **long_term_competitiveness**: 1=強調長期競爭力, 0=沒有
8. **short_term_focus**: 1=專注短期市場, 0=沒有
9. **ceo_leadership_style**: 1=提及 CEO 管理風格, 0=沒有
10. **earnings_expectation_gap**: 收益預期差距 (-1 到 1)
11. **stock_price_growth_trend**: 股價趨勢 (-1 到 1)
12. **market_demand**: 市場需求 (-1 到 1)
13. **market_capitalization**: 1=提及市值, 0=沒有
14. **target_price**: 1=提及目標價, 0=沒有
15. **financial_health**: 財務健康度 (-1 到 1)
16. **valuation**: 估值評估 (-1=高估, 1=低估)
17. **policy_impact**: 政策影響 (-1 到 1)
18. **like_number**: 按讚數（從 videos 資料表取得）
19. **comment_number**: 評論數（從 videos 資料表取得）
20. **raw_json**: 原始 Gemini 回應 JSON

## 資料庫查詢範例

```bash
# 進入 Python 並查詢分析結果
python3
```

```python
from db_manager import DatabaseManager

db = DatabaseManager()
db.connect()

# 查詢所有已分析的影片
db.cursor.execute("""
    SELECT v.title, f.stock_ticker, f.video_sentiment, f.financial_ratio
    FROM Youtuber_Financial_Data f
    JOIN videos v ON f.video_id = v.video_id
""")

for row in db.cursor.fetchall():
    print(f"標題: {row['title']}")
    print(f"  股票: {row['stock_ticker']}")
    print(f"  情感: {row['video_sentiment']}")
    print(f"  財務比例: {row['financial_ratio']}")
    print()

db.close()
```

## 故障排除

### 錯誤: "You do not currently have an active account selected"
**解決方法**: 執行 `gcloud auth login` 並完成瀏覽器驗證

### 錯誤: "Service account key file not found"
**解決方法**: 確認 `GOOGLE_APPLICATION_CREDENTIALS` 環境變數指向正確的 JSON 金鑰檔案路徑

### 錯誤: "Permission denied: aiplatform.googleapis.com"
**解決方法**:
1. 確認專案已啟用 Vertex AI API
2. 確認您的帳戶有 `roles/aiplatform.user` 權限

### 錯誤: "JSON decode error"
**解決方法**: Gemini 回應格式可能不正確，腳本會自動重試 3 次

## API 配額管理

- Vertex AI Gemini API 有 RPM (每分鐘請求) 限制
- 批次分析時，腳本會在每次請求間等待 2 秒
- 建議分批處理大量影片，每批 10-20 個

## 下一步

完成以上步驟後，您就可以：

1. ✅ 搜尋 YouTube 影片並存入資料庫
2. ✅ 使用 Gemini AI 分析影片內容
3. ✅ 將分析結果儲存到資料庫
4. 🔜 建立資料分析與視覺化工具
5. 🔜 建立批次處理腳本（遍歷所有 YouTuber）

## 聯絡資訊

如有問題，請參考：
- [Google Gen AI SDK 文件](https://cloud.google.com/vertex-ai/generative-ai/docs/sdks/overview)
- [Vertex AI Gemini 文件](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini)
