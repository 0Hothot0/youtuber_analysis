# Comment Sentiment 分析改進指南

## 📊 當前狀態

根據最新報告 (2026-03-12)：

| 資料庫 | 總記錄數 | 已完成 | 待處理 | 進度 |
|--------|---------|--------|--------|------|
| Joseph 2年期 | 466 | 0 | 466 | 0% |
| Joseph 3個月 | 466 | 0 | 466 | 0% |
| Single 2年期 | 123 | 23 | 100 | 18.7% |
| Single 3個月 | 123 | 23 | 100 | 18.7% |
| **總計** | **1,178** | **46** | **1,132** | **3.9%** |

**預估完成時間**: 約 3.8 小時

---

## 🚀 快速開始

### 1. 查看當前狀態

```bash
# 生成完整狀態報告
python3 scripts/report_comment_sentiment_status.py
```

### 2. 開始分析（推薦順序）

```bash
# 步驟 1: 先處理 Joseph 2年期 (466筆待處理)
python3 scripts/analyze_single_comments_improved.py --db joseph_2years

# 步驟 2: 處理 Single 2年期 (100筆待處理)
python3 scripts/analyze_single_comments_improved.py --db single_2years

# 步驟 3: 處理 Joseph 3個月
python3 scripts/analyze_single_comments_improved.py --db joseph_3months

# 步驟 4: 處理 Single 3個月
python3 scripts/analyze_single_comments_improved.py --db single_3months
```

### 3. 一次處理所有資料庫

```bash
# 批次處理所有 single 資料庫
python3 scripts/analyze_single_comments_improved.py --db all
```

---

## 📚 詳細使用說明

### 分析工具：`analyze_single_comments_improved.py`

#### 基本用法

```bash
# 分析指定資料庫
python3 scripts/analyze_single_comments_improved.py --db <資料庫名稱>
```

#### 可用的資料庫選項

- `joseph_2years` - Joseph 2年期資料庫
- `joseph_3months` - Joseph 3個月資料庫
- `single_2years` - Single 2年期資料庫
- `single_3months` - Single 3個月資料庫
- `all` - 所有資料庫

#### 進階選項

```bash
# 測試模式（不實際更新資料庫）
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --dry-run

# 限制處理數量（測試用）
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --limit 5

# 清除進度重新開始
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --reset-progress

# 組合使用
python3 scripts/analyze_single_comments_improved.py \
    --db joseph_2years \
    --limit 10 \
    --dry-run
```

### 報告工具：`report_comment_sentiment_status.py`

```bash
# 生成當前狀態報告
python3 scripts/report_comment_sentiment_status.py
```

報告內容包含：
- ✅ 各資料庫處理進度
- ✅ 情緒統計（正面/負面）
- ✅ 詳細分佈圖
- ✅ 預估完成時間

---

## ✨ 改進功能特點

### 1. 智能重試機制

- 自動處理 API 失敗
- 多區域回退（us-central1 → us-east4 → us-west1）
- 多模型嘗試（flash → pro）

### 2. 進度自動保存

- 每處理 10 個影片自動保存進度
- 中途中斷可續接（使用 `.comment_analysis_progress.json`）
- 按 `Ctrl+C` 中斷後下次自動從上次停止處繼續

### 3. 詳細錯誤分類

腳本會區分不同類型的結果：
- ✅ **成功** - 成功分析情緒
- 🚫 **留言關閉** - 影片關閉留言功能
- 📭 **無留言** - 影片沒有留言（sentiment = 0.0）
- ❌ **API 錯誤** - YouTube 或 Gemini API 失敗

### 4. 彈性資料庫選擇

- 可選擇單一資料庫
- 可一次處理所有資料庫
- 自動檢查資料庫是否存在

---

## 🔧 處理流程

### 單一影片處理流程

```
1. 抓取影片留言 (YouTube API)
   ↓
2. 檢查留言狀態
   - 留言關閉 → sentiment = NULL
   - 無留言 → sentiment = 0.0
   - 有留言 → 繼續步驟 3
   ↓
3. 分析留言情緒 (Gemini API)
   - 使用 Gemini 1.5 Flash/Pro
   - 回傳 -1 ~ 1 之間的分數
   ↓
4. 更新資料庫
   - 更新該 video_id 的所有記錄
   - 保存進度
```

### API 延遲設定

- **YouTube API**: 0.5 秒（避免 quota 限制）
- **Gemini API**: 10 秒（避免 rate limit）

---

## 📈 實用場景

### 場景 1: 首次完整分析

```bash
# 先測試 5 個影片
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --limit 5

# 確認無誤後完整執行
python3 scripts/analyze_single_comments_improved.py --db joseph_2years
```

### 場景 2: 中途中斷後續接

```bash
# 第一次執行（處理了 30 個影片後按 Ctrl+C）
python3 scripts/analyze_single_comments_improved.py --db joseph_2years

# 下次執行會自動從第 31 個開始
python3 scripts/analyze_single_comments_improved.py --db joseph_2years
```

### 場景 3: 批次處理所有資料庫

```bash
# 一次處理所有（適合晚上或週末執行）
python3 scripts/analyze_single_comments_improved.py --db all

# 預估時間：約 3-4 小時
```

### 場景 4: 查看進度

```bash
# 在另一個終端視窗執行
watch -n 60 python3 scripts/report_comment_sentiment_status.py

# 每 60 秒自動更新一次報告
```

---

## ⚠️ 注意事項

### API 配額限制

1. **YouTube Data API v3**
   - 預設每日配額：10,000 units
   - `search.list`: ~100 units
   - `videos.list`: ~1 unit
   - `commentThreads.list`: ~1 unit

2. **Google Vertex AI Gemini**
   - 免費層級可能有 RPM (每分鐘請求數) 限制
   - 腳本已設定 10 秒延遲避免超過限制
   - 如遇到 429 錯誤，可手動增加 `GEMINI_DELAY`

### 錯誤處理

如果出現大量 API 錯誤：

```bash
# 1. 檢查 API 配額
# 前往 Google Cloud Console 查看配額使用情況

# 2. 清除進度重新開始
python3 scripts/analyze_single_comments_improved.py \
    --db joseph_2years \
    --reset-progress

# 3. 減少批次大小
python3 scripts/analyze_single_comments_improved.py \
    --db joseph_2years \
    --limit 20
```

### 進度檔案

- 位置：`.comment_analysis_progress.json`
- 內容：已處理的 video_id 列表
- 可手動刪除重新開始：`rm .comment_analysis_progress.json`

---

## 📝 輸出範例

### 執行中的輸出

```
================================================================================
Single 資料庫留言情緒分析 (改進版)
================================================================================

初始化 API 客戶端... 完成
  ✓ Gemini API: us-central1 / gemini-1.5-flash-001

================================================================================
處理資料庫: youtube_analysis_2years_single_joseph.db
================================================================================

資料庫狀態:
  總記錄數: 466
  唯一影片數: 92
  待處理: 466
  已完成: 0

待處理影片: 92 個
預計時間:約 18.4 分鐘

[1/92]
  處理影片: dQw4w9WgXcQ (UUID: a1b2c3d4...)
    [1/2] 抓取留言... 找到 150 則留言
    [2/2] 分析情緒... 完成 (分數: 0.723)
    ✓ 更新 5 筆記錄

[2/92]
  處理影片: jNQXAC9IVRw (UUID: e5f6g7h8...)
    [1/2] 抓取留言... 留言已關閉
    ✓ 更新 3 筆記錄
```

### 完成後的摘要

```
--------------------------------------------------------------------------------
資料庫處理完成: youtube_analysis_2years_single_joseph.db
--------------------------------------------------------------------------------
成功: 85
失敗: 2
留言關閉: 3
無留言: 2
API 錯誤: 2

================================================================================
所有資料庫處理完成
================================================================================
總計成功: 85
總計失敗: 2

✓ 已更新 comment_sentiment 欄位
================================================================================
```

---

## 🎯 建議執行策略

### 策略 A: 分階段執行（推薦）

適合需要監控進度或 API 配額有限的情況：

```bash
# Day 1: 處理 Joseph 2年期 (最大的資料庫)
python3 scripts/analyze_single_comments_improved.py --db joseph_2years

# Day 2: 處理其他資料庫
python3 scripts/analyze_single_comments_improved.py --db joseph_3months
python3 scripts/analyze_single_comments_improved.py --db single_2years
python3 scripts/analyze_single_comments_improved.py --db single_3months
```

### 策略 B: 一次完成

適合配額充足且希望快速完成的情況：

```bash
# 一次處理所有資料庫（約 3-4 小時）
python3 scripts/analyze_single_comments_improved.py --db all
```

### 策略 C: 測試優先

適合首次使用或需要驗證的情況：

```bash
# Step 1: 小規模測試
python3 scripts/analyze_single_comments_improved.py \
    --db joseph_2years \
    --limit 3 \
    --dry-run

# Step 2: 實際測試
python3 scripts/analyze_single_comments_improved.py \
    --db joseph_2years \
    --limit 3

# Step 3: 查看結果
python3 scripts/report_comment_sentiment_status.py

# Step 4: 確認無誤後完整執行
python3 scripts/analyze_single_comments_improved.py --db joseph_2years
```

---

## 🔍 故障排除

### 問題 1: Gemini API 初始化失敗

```
❌ 無法初始化 Gemini API
請檢查:
  1. Google Cloud 專案權限
  2. Vertex AI API 是否啟用
  3. 帳號配額是否足夠
```

**解決方法**:
1. 確認 `.env` 中的 `GOOGLE_CLOUD_PROJECT` 正確
2. 在 Google Cloud Console 啟用 Vertex AI API
3. 檢查服務帳號權限

### 問題 2: YouTube API 配額不足

```
YouTube API 錯誤: quotaExceeded
```

**解決方法**:
1. 等待配額重置（每日 00:00 PST）
2. 使用 `--limit` 參數減少每次處理數量
3. 申請提高 YouTube API 配額

### 問題 3: 進度檔案損壞

```
⚠ 無法載入進度檔案: ...
```

**解決方法**:
```bash
# 刪除進度檔案重新開始
rm .comment_analysis_progress.json

# 或使用 --reset-progress
python3 scripts/analyze_single_comments_improved.py \
    --db joseph_2years \
    --reset-progress
```

---

## 📞 需要協助？

如果遇到問題：
1. 先執行狀態報告確認當前狀態
2. 使用 `--dry-run` 測試模式排查
3. 查看 `.comment_analysis_progress.json` 確認進度
4. 檢查 Google Cloud Console 的 API 配額使用情況

---

## 🎉 完成後

所有分析完成後，你將擁有：
- ✅ 完整的留言情緒分數 (-1 到 1)
- ✅ 留言關閉狀態標記 (NULL)
- ✅ 無留言標記 (0.0)
- ✅ 詳細的情緒統計報告

可以用於：
- 📊 分析影片受歡迎程度
- 📈 研究情緒與股價預測準確度的關係
- 🔍 識別高品質內容（高情緒分數）
- 📉 追蹤特定 YouTuber 的觀眾反應趨勢
