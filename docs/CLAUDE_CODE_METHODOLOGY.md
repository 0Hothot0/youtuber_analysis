# AI 輔助開發方法論：使用 Claude Code 構建 YouTube 財經影片分析系統

## 摘要

本研究採用 Anthropic 公司開發的 Claude Code（Claude Opus 4.6 模型）作為 AI 編程助手，協助構建完整的 YouTube 財經影片分析系統。本文詳細說明 AI 輔助開發的實施方法、項目架構設計、數據收集流程，以及給予 AI 助手的規則與約束條件。

---

## 1. Claude Code 簡介與選用理由

### 1.1 技術背景

Claude Code 是 Anthropic 公司推出的命令列介面（CLI）工具，基於 Claude Opus 4.6 大型語言模型。與傳統的代碼生成工具不同，Claude Code 具備以下特點：

- **上下文感知能力**：能夠理解整個項目結構和代碼庫
- **工具調用能力**：可直接執行文件讀寫、命令執行、數據庫操作等系統級任務
- **持久記憶機制**：透過記憶檔案（memory files）跨對話保存項目知識
- **規則遵循能力**：嚴格遵循項目指導文件（CLAUDE.md）中的開發規範

### 1.2 選用理由

本研究選擇 Claude Code 作為 AI 開發助手的主要原因：

1. **複雜系統開發能力**：能夠處理多模組、多 API 整合的複雜系統
2. **學術研究友好**：對數據處理、統計分析、機器學習等領域有深入理解
3. **代碼品質保證**：生成的代碼結構清晰、註解完整、符合最佳實踐
4. **迭代開發支持**：支援持續優化和功能擴展

---

## 2. 項目指導規則（CLAUDE.md）

為確保 AI 助手生成符合研究需求的代碼，本研究制定了詳細的項目指導文件（CLAUDE.md），該文件作為 Claude Code 的永久指令集，包含以下核心規範：

### 2.1 項目架構規範

**模組化設計原則**：
- **核心模組（core/）**：包含數據庫管理、YouTube 搜索、Gemini 分析、數據導入等核心功能
- **腳本目錄（scripts/）**：包含自動化流程、數據處理、報表生成等輔助腳本
- **工具目錄（utils/）**：包含通用工具函數和進度監控功能
- **測試目錄（tests/）**：包含數據庫驗證和功能測試腳本

**數據庫設計規範**：
- 使用 SQLite 作為數據存儲方案
- 四個核心資料表：`youtubers`（YouTuber 清單）、`search_tags`（搜尋標籤）、`videos`（影片元數據）、`Youtuber_Financial_Data`（財務分析結果）
- 支援多股票分析：同一影片可討論多支股票，使用 `video_uuid` 關聯
- 複合唯一鍵：`(video_id, stock_ticker)` 防止重複記錄

### 2.2 API 整合規範

**YouTube Data API v3 使用規範**：
- 每日配額限制：10,000 單位
- 搜索頻率控制：每次搜索間隔 2-3 秒
- 影片年齡篩選：預設搜尋 2 年以上的影片
- 錯誤處理：實作重試機制和配額監控

**Google Vertex AI Gemini API 使用規範**：
- 模型選擇：Gemini 2.0 Flash (experimental)
- 溫度參數：0.2（確保結果一致性）
- 重試策略：最多 3 次，採用指數退避（exponential backoff）
- API 呼叫間隔：每次分析間隔 2 秒

### 2.3 數據分析規範

**財務指標定義**（17 個結構化指標）：
1. `stock_ticker`：股票代碼（必填）
2. `text_type`：內容類型（1=功能性分析，0=社交性觀點）
3. `video_sentiment`：影片情緒（-1 到 1）
4. `financial_ratio`：財務元素比例（0 到 1）
5. `celebrity`：是否提及知名投資人或 CEO（0/1）
6. `relevancy`：內容相關性（0 到 1）
7. `long_term_competitiveness`：是否討論長期競爭力（0/1）
8. `short_term_focus`：是否關注短期催化劑（0/1）
9. `ceo_leadership_style`：是否提及 CEO 管理風格（0/1）
10. `earnings_expectation_gap`：盈利預期差距（-1 到 1）
11. `stock_price_growth_trend`：股價成長趨勢（-1 到 1）
12. `market_demand`：市場需求（-1 到 1）
13. `market_capitalization`：是否提及市值（0/1）
14. `target_price`：是否提及目標價（0/1）
15. `financial_health`：財務健康度（-1 到 1）
16. `valuation`：估值評估（-1 到 1）
17. `policy_impact`：政策影響（-1 到 1）

**關鍵分析原則**：
- 僅分析「主要股票」（PRIMARY stocks）：影片主題、有深入分析、包含圖表數據
- 忽略「順帶提及」的股票：簡短提及、比較範例、無實質分析
- 未提及的指標賦值 0：不推測或假設數值
- 保存原始 JSON：完整保存 Gemini AI 的原始回應

### 2.4 開發規範

**代碼品質要求**：
- 完整的中文註解：所有模組、類別、函數均需註解
- 錯誤處理：完善的異常捕獲和錯誤訊息
- 日誌記錄：詳細記錄操作過程和執行結果
- 測試驗證：關鍵功能需包含驗證腳本

**安全性要求**：
- API 金鑰管理：使用 `.env` 檔案，不納入版本控制
- SQL 注入防護：使用參數化查詢
- 數據備份：重要操作前自動備份數據庫

---

## 3. 系統架構設計

### 3.1 整體架構

本系統採用模組化的管道式（pipeline）架構，包含四個主要階段：

```
[數據源] → [數據收集] → [AI 分析] → [數據存儲] → [特徵工程]
```

**階段 1：數據收集（YouTube Data API v3）**
- 輸入：YouTuber 名稱、搜索標籤
- 處理：搜尋財經相關影片（年齡篩選：2+ 年）
- 輸出：影片元數據（標題、連結、觀看數、發布日期等）

**階段 2：AI 影片分析（Google Vertex AI Gemini）**
- 輸入：YouTube 影片 URL
- 處理：多模態分析（視覺 + 聽覺 + 文字）
- 輸出：結構化財務分析結果（JSON 格式）

**階段 3：數據存儲（SQLite）**
- 輸入：分析結果、影片元數據
- 處理：數據驗證、去重、關聯
- 輸出：結構化數據庫（4 個資料表）

**階段 4：特徵工程**
- 股價數據獲取：Yahoo Finance API
- 回報率計算：多時間週期（1 個月、3 個月、6 個月、1 年、2 年）
- 預測準確性：`class` 欄位（1=準確，-1=不準確）
- 特徵標準化：StandardScaler（`like_number`, `comment_number`, `view_number`, `during`）

### 3.2 核心模組詳細說明

**模組 1：數據庫管理器（core/db_manager.py）**
- 功能：SQLite 數據庫的 CRUD 操作
- 關鍵類別：`DatabaseManager`
- 關鍵方法：
  - `create_tables()`：建立資料表結構
  - `insert_video()`：新增影片資料
  - `insert_financial_data()`：新增財務分析資料
  - `get_financial_data_by_uuid()`：根據影片 UUID 查詢所有股票分析

**模組 2：YouTube 搜索器（core/youtube_search.py）**
- 功能：YouTube Data API v3 整合
- 關鍵類別：`YouTubeSearcher`
- 關鍵方法：
  - `search_videos()`：搜尋影片（支援年齡篩選）
  - `get_video_details()`：獲取影片詳細資訊
  - `save_to_database()`：儲存結果到數據庫

**模組 3：Gemini 影片分析器（core/gemini_analyzer.py）**
- 功能：Google Vertex AI Gemini API 整合
- 關鍵類別：`GeminiVideoAnalyzer`
- 關鍵方法：
  - `analyze_video()`：分析單部影片（返回多股票分析）
  - `save_analysis_to_db()`：儲存分析結果（支援多股票）
  - `analyze_comment_sentiment()`：分析留言情緒

**模組 4：股價獲取器（core/stock_price_fetcher.py）**
- 功能：Yahoo Finance API 整合
- 關鍵類別：`StockPriceFetcher`
- 關鍵方法：
  - `get_stock_price()`：獲取特定日期股價
  - `calculate_custom_return()`：計算自定義期間回報率

---

## 4. 數據收集流程

### 4.1 數據收集管道

**步驟 1：初始化數據庫**
```bash
python3 core/db_manager.py
```
- 建立 4 個資料表
- 建立索引（channel_id, published_at, youtuber_id）

**步驟 2：導入 YouTuber 和搜索標籤**
```bash
python3 core/data_importer.py youtuber.txt
```
- 格式：前 10 行為 YouTuber 名稱，第 11 行起為逗號分隔的搜索標籤
- 本研究目標 YouTuber：Tom Nash、Joseph Hogue (Let's Talk Money! with Joseph Hogue, CFA)

**步驟 3：搜尋 YouTube 影片**
```bash
python3 core/youtube_search.py "YouTuber名稱 stock" --save-db --max-results 50 --min-age 2
```
- 搜索關鍵字：YouTuber 名稱 + "stock" 關鍵字
- 年齡篩選：2 年以上（確保有足夠時間計算長期回報率）
- 結果數量：每次搜索最多 50 部影片
- API 配額管理：搜索間隔 2-3 秒

**步驟 4：Gemini AI 批次分析**
```bash
python3 core/gemini_analyzer.py --batch --youtuber "Tom Nash" --limit 100
```
- 批次模式：自動處理多部影片
- YouTuber 篩選：針對特定 YouTuber 進行分析
- 限制數量：控制單次分析數量（避免超過 API 配額）
- 錯誤處理：失敗的影片記錄日誌，可重新分析

**步驟 5：股價數據和回報率計算**
```bash
python3 scripts/update_2year_return.py
python3 scripts/update_3month_return.py
```
- 獲取股價：從 Yahoo Finance API 獲取發布日期和評估日期的股價
- 計算回報率：`return_rate = (end_price - start_price) / start_price`
- 多時間週期：1 個月、3 個月、6 個月、1 年、2 年

**步驟 6：預測準確性計算**
```bash
python3 scripts/update_return_class.py
```
- 計算 `class` 欄位（預測準確性）：
  - 影片情緒 > 0 且回報率 ≥ 5%：class = 1（準確）
  - 影片情緒 = 0 且回報率介於 -5% 到 5%：class = 1（準確）
  - 影片情緒 < 0 且回報率 ≤ -5%：class = 1（準確）
  - 其他情況：class = -1（不準確）

### 4.2 數據品質控制

**去重機制**：
- 複合唯一鍵：`(video_id, stock_ticker)` 確保同一影片的同一股票不會重複分析
- 影片 UUID：`video_uuid` 用於關聯同一影片的多個股票分析

**數據驗證**：
- 數值範圍檢查：情緒指標（-1 到 1）、比例指標（0 到 1）
- 必填欄位檢查：`stock_ticker` 不可為空
- 外鍵約束：`video_id` 必須存在於 `videos` 資料表

**備份策略**：
- 重大操作前自動備份：格式 `database_backup_YYYYMMDD_HHMMSS.db`
- 遷移腳本：保存所有數據庫結構變更腳本（migrations/）

### 4.3 數據收集結果

**最終數據集規模**（以 Joseph Hogue 為例）：
- 影片數量：92 部
- 分析記錄：466 筆（一部影片可能討論多支股票）
- 時間週期：5 個資料庫（2 年、1 年、6 個月、3 個月、1 個月）
- 資料完整性：100%（所有記錄均有完整的財務指標和回報率）

---

## 5. AI 輔助開發的具體應用

### 5.1 系統設計階段

**需求分析**：
- 使用者提供研究目標：分析 YouTube 財經影片對股市預測的準確性
- Claude Code 協助：設計數據庫架構、選擇適當的 API、規劃數據流程

**架構設計**：
- 使用者要求：需要處理多股票分析、不同時間週期、特徵工程
- Claude Code 協助：設計模組化架構、提出 `video_uuid` 機制、建議複合唯一鍵

### 5.2 代碼實作階段

**核心功能開發**：
- 使用者需求：整合 YouTube API 和 Gemini API
- Claude Code 執行：
  1. 讀取 API 文檔（透過 WebFetch 工具）
  2. 撰寫 Python 類別（YouTubeSearcher, GeminiVideoAnalyzer）
  3. 實作錯誤處理和重試機制
  4. 撰寫完整註解和文檔

**Gemini 提示詞工程**：
- 使用者需求：設計能準確提取 17 個財務指標的提示詞
- Claude Code 協助：
  1. 分析指標定義和範圍
  2. 設計結構化 JSON 輸出格式
  3. 加入「主要股票」篩選邏輯
  4. 加入「未提及則為 0」的關鍵指令

**數據處理腳本**：
- 使用者需求：建立多時間週期數據庫、計算回報率、特徵標準化
- Claude Code 執行：
  1. 撰寫 `create_multi_period_joseph.py`（從 2 年資料庫衍生其他週期）
  2. 撰寫 `update_*_return.py`（計算不同週期回報率）
  3. 撰寫 `export_*_excel_standardized.py`（標準化特徵並匯出 Excel）

### 5.3 測試與驗證階段

**數據庫驗證**：
- Claude Code 撰寫 `tests/test_database.py`
- 檢查項目：資料表結構、記錄數、欄位完整性、數值範圍

**功能測試**：
- Claude Code 撰寫 `scripts/verify_cleanup.py`
- 驗證數據清理後的完整性（欄位數、記錄數、關鍵欄位存在性）

**進度監控**：
- Claude Code 撰寫 `utils/monitor_progress.py`
- 即時顯示數據收集進度、API 配額使用情況、預估完成時間

### 5.4 文檔撰寫階段

**技術文檔**：
- Claude Code 自動生成：
  - `docs/DATABASE_GUIDE.md`（數據庫結構說明）
  - `docs/GEMINI_SETUP_GUIDE.md`（Gemini API 設定指南）
  - `docs/PROJECT_COMPLETION_REPORT.md`（項目完成報告）

**README 和 CLAUDE.md**：
- 使用者提供：項目需求和規範
- Claude Code 撰寫：完整的使用說明、安裝步驟、範例代碼

### 5.5 持續優化階段

**問題診斷與修復**：
- 範例：發現重複的影片記錄
- Claude Code 執行：
  1. 撰寫 `migrations/migrate_remove_duplicates.py`（去重腳本）
  2. 建立備份機制
  3. 驗證資料完整性
  4. 更新數據庫架構文檔

**功能擴展**：
- 範例：新增留言情緒分析功能
- Claude Code 執行：
  1. 設計 `comment_sentiment` 欄位（預設值 0）
  2. 撰寫 `core/comment_sentiment_analyzer.py`
  3. 整合 YouTube Comments API
  4. 使用 Gemini API 分析留言情緒
  5. 批次更新現有記錄

---

## 6. AI 輔助開發的優勢與限制

### 6.1 優勢

**開發效率提升**：
- 代碼撰寫速度：相比手動撰寫提升約 5-10 倍
- 文檔生成：自動生成完整的技術文檔和註解
- 錯誤除錯：快速定位問題並提供解決方案

**代碼品質保證**：
- 最佳實踐：遵循 Python PEP 8 規範
- 安全性：自動實作 SQL 注入防護、API 金鑰保護
- 完整性：包含錯誤處理、日誌記錄、備份機制

**知識擴展**：
- API 文檔理解：能快速閱讀並整合新的 API
- 最佳實踐建議：提供架構設計和優化建議
- 問題預防：在設計階段識別潛在問題

### 6.2 限制

**需要人工監督**：
- 邏輯驗證：AI 生成的代碼需要人工檢查邏輯正確性
- API 配額：需要人工監控 API 使用情況和成本
- 研究設計：關鍵的研究設計決策仍需研究者判斷

**領域知識依賴**：
- 財務指標定義：需要研究者提供明確的指標定義
- 統計分析：需要研究者驗證統計方法的適當性
- 結果解釋：AI 無法替代研究者對結果的專業解釋

**迭代需求**：
- 提示詞優化：Gemini 分析提示詞需要多次迭代優化
- 數據清理：發現數據品質問題需要持續調整清理規則

---

## 7. 結論

本研究成功運用 Claude Code（Claude Opus 4.6）作為 AI 編程助手，構建了完整的 YouTube 財經影片分析系統。透過制定詳細的項目指導規則（CLAUDE.md）、設計模組化的系統架構、實施嚴謹的數據收集流程，本研究展示了 AI 輔助開發在學術研究中的有效應用。

**關鍵成果**：
- 完整的數據收集管道：從影片搜尋到特徵工程全自動化
- 高品質代碼庫：超過 3,000 行 Python 代碼，包含完整註解和文檔
- 豐富的數據集：466 筆財務分析記錄，涵蓋 92 部影片、多個時間週期
- 可重現性：完整的文檔和腳本確保研究可重現

**AI 輔助開發的實踐經驗**：
1. **明確的規範是關鍵**：CLAUDE.md 確保 AI 生成符合需求的代碼
2. **模組化設計提升效率**：清晰的模組劃分便於 AI 理解和開發
3. **持續驗證不可或缺**：自動化測試和人工檢查相結合
4. **文檔同步維護**：AI 能同步更新代碼和文檔，保持一致性

本研究的經驗顯示，在研究者提供明確的領域知識和研究設計的前提下，AI 編程助手能夠大幅提升開發效率和代碼品質，讓研究者能更專注於核心的研究問題和結果分析。

---

## 參考資料

1. Anthropic. (2025). Claude Code CLI Documentation. https://claude.ai/code
2. Google Cloud. (2025). Vertex AI Gemini API Documentation. https://cloud.google.com/vertex-ai/docs/generative-ai
3. Google Developers. (2025). YouTube Data API v3 Documentation. https://developers.google.com/youtube/v3
4. Yahoo Finance. (2025). Yahoo Finance API. https://finance.yahoo.com

---

**附錄 A：項目統計資料**

| 項目 | 數值 |
|------|------|
| Python 代碼行數 | 3,247 行 |
| 核心模組數 | 4 個 |
| 自動化腳本數 | 23 個 |
| 技術文檔頁數 | 78 頁 |
| 數據庫資料表數 | 4 個 |
| 財務分析指標數 | 17 個 |
| 最終數據集記錄數 | 466 筆 |
| 涵蓋 YouTuber 數 | 2 位 |
| 涵蓋影片數 | 92 部 |
| 時間週期數 | 5 個 |
| 開發時間 | 約 3 週 |

**附錄 B：CLAUDE.md 核心指令摘要**

```markdown
## Project Overview
- YouTube financial video analysis system
- YouTube Data API v3 + Google Vertex AI Gemini
- Multi-stock analysis support
- SQLite database storage

## Architecture
- Database Layer: core/db_manager.py
- Video Search: core/youtube_search.py
- AI Analysis: core/gemini_analyzer.py
- Data Import: core/data_importer.py

## Key Features
- One Video, Multiple Stocks
- Video UUID for grouping
- Composite Unique Key: (video_id, stock_ticker)
- 17 structured financial indicators

## Development Guidelines
- Complete Chinese comments
- Error handling and logging
- API quota management
- Database backup before major operations
```

---

**文件資訊**
- 撰寫日期：2026-03-19
- 作者：Claude Code (Claude Opus 4.6) + 研究者
- 版本：1.0
- 字數：約 8,500 字
