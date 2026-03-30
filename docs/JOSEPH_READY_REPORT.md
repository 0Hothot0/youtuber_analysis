# Joseph Hogue 評論情感分析 - 就緒報告

## 📋 當前狀態

### ✅ 已完成的準備工作

1. **數據庫創建**
   - ✅ `youtube_analysis_2years_single_joseph.db` (2.1 MB, 466 條記錄, 92 個視頻)
   - ✅ `youtube_analysis_3months_single_joseph.db` (1.9 MB, 466 條記錄, 31 個視頻)

2. **Excel 導出**
   - ✅ `exports/youtube_analysis_2years_single_joseph.xlsx` (226 KB)
   - ✅ `exports/youtube_analysis_3months_single_joseph.xlsx` (226 KB)
   - 每個文件包含 All_Data, Train (80%), Test (20%), Statistics 四個 sheets

3. **分析工具**
   - ✅ `scripts/analyze_joseph_comments.py` - 專門的評論分析腳本
   - ✅ `scripts/export_joseph_to_excel.py` - Excel 導出腳本
   - ✅ `scripts/create_youtuber_db_by_name.py` - 通用數據庫創建腳本

4. **文檔**
   - ✅ `docs/JOSEPH_COMMENT_ANALYSIS_GUIDE.md` - 完整使用指南

### ⏳ 等待中

**Gemini API 狀態**:
- ❌ **BILLING_DISABLED** (計費功能未啟用)
- 錯誤碼: `403 PERMISSION_DENIED`
- 項目: `carbon-scene-480709-t1`

**問題原因**:
Google Cloud 項目需要啟用 billing 才能使用 Vertex AI Gemini API 進行評論情感分析。

## 🚀 當 API 更新後立即執行

### 快速啟動（推薦）

```bash
# 方法 1: 測試單個視頻（確認 API 可用）
python3 scripts/analyze_joseph_comments.py --limit 1

# 方法 2: 小批次測試（處理 5 個視頻）
python3 scripts/analyze_joseph_comments.py --limit 5

# 方法 3: 完整批次處理（所有 92 個視頻）
python3 scripts/analyze_joseph_comments.py

# 方法 4: 只處理 2years 數據庫
python3 scripts/analyze_joseph_comments.py --database 2years
```

### 詳細步驟

```bash
# 步驟 1: 確認環境（可選）
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('✓ YOUTUBE_API_KEY:', 'OK' if os.getenv('YOUTUBE_API_KEY') else '❌')
print('✓ GOOGLE_CLOUD_PROJECT:', 'OK' if os.getenv('GOOGLE_CLOUD_PROJECT') else '❌')
"

# 步驟 2: 測試 API 連接（dry-run）
python3 scripts/analyze_joseph_comments.py --limit 1 --dry-run

# 步驟 3: 開始批次處理
python3 scripts/analyze_joseph_comments.py

# 預計時間: 約 15-25 分鐘（92 個視頻 × 15 秒/視頻）

# 步驟 4: 重新導出 Excel（包含 comment_sentiment）
python3 scripts/export_joseph_to_excel.py
```

## 📊 數據庫當前狀態

### youtube_analysis_2years_single_joseph.db
- 總記錄: 466
- 唯一視頻: 92
- comment_sentiment = 0: 466 (待分析)
- comment_sentiment 已分析: 0
- comment_sentiment IS NULL: 0

### youtube_analysis_3months_single_joseph.db
- 總記錄: 466
- 唯一視頻: 31
- comment_sentiment = 0: 466 (待分析)
- comment_sentiment 已分析: 0
- comment_sentiment IS NULL: 0

## 📈 預期結果

完成後，每個視頻的 comment_sentiment 將會是：
- **正數 (0.1 ~ 1.0)**: 正面情緒
- **負數 (-1.0 ~ -0.1)**: 負面情緒
- **0.0**: 沒有評論或中性
- **NULL**: 評論已關閉

## 🔧 API 配額使用預估

### YouTube Data API v3
- 92 個視頻 × 1 unit = **約 92 units**
- 每日配額: 10,000 units
- ✅ 配額充足

### Vertex AI Gemini API
- 92 個視頻 × 1 次調用 = **92 次調用**
- 使用模型: `gemini-1.5-flash-001`
- 間隔時間: 10 秒/次
- ⏳ 需要啟用 billing

## 📝 腳本功能說明

### scripts/analyze_joseph_comments.py

**主要功能:**
- 從 Joseph 的數據庫中獲取所有待分析視頻
- 使用 YouTube API 抓取評論
- 使用 Gemini AI 分析評論情感
- 自動更新數據庫的 comment_sentiment 字段
- 支持中斷恢復（Ctrl+C 後可繼續）

**參數選項:**
```
--database {2years,3months,both}  選擇數據庫（預設: both）
--limit N                         限制處理 N 個視頻（測試用）
--dry-run                         測試模式（不更新數據庫）
--resume                          繼續未完成的分析
```

**錯誤處理:**
- ✅ 評論關閉 → comment_sentiment = NULL
- ✅ 無評論 → comment_sentiment = 0.0
- ✅ API 失敗 → 跳過該視頻
- ✅ 第一個視頻失敗 → 立即停止（避免浪費配額）

## 🛠️ 故障排除

### 如果遇到錯誤...

**1. BILLING_DISABLED (當前狀況)**
```
✓ 啟用 Google Cloud Billing
✓ 等待幾分鐘讓設置生效
✓ 重新運行腳本
```

**2. Rate Limit Exceeded**
```bash
# 使用較小的批次
python3 scripts/analyze_joseph_comments.py --limit 10

# 等待配額重置後繼續
python3 scripts/analyze_joseph_comments.py --resume
```

**3. 第一個視頻就失敗**
```bash
# 檢查 API 密鑰
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('YOUTUBE_API_KEY')[:20])"

# 檢查網絡連接
curl -I https://www.googleapis.com/
```

## 📁 相關文件索引

```
youtuber_analysis/
├── youtube_analysis_2years_single_joseph.db    # Joseph 2years 數據庫
├── youtube_analysis_3months_single_joseph.db   # Joseph 3months 數據庫
│
├── scripts/
│   ├── analyze_joseph_comments.py              # 評論分析主腳本 ⭐
│   ├── export_joseph_to_excel.py               # Excel 導出腳本
│   └── create_youtuber_db_by_name.py           # 數據庫創建腳本
│
├── exports/
│   ├── youtube_analysis_2years_single_joseph.xlsx
│   └── youtube_analysis_3months_single_joseph.xlsx
│
├── docs/
│   ├── JOSEPH_COMMENT_ANALYSIS_GUIDE.md        # 詳細使用指南
│   └── JOSEPH_READY_REPORT.md                  # 本文件
│
└── .env                                        # API 密鑰配置
```

## ✅ 檢查清單

在運行分析前，確認：

- [x] Joseph 數據庫已創建（2years + 3months）
- [x] Excel 文件已導出（初始版本）
- [x] 分析腳本已準備好
- [x] YouTube API 密鑰已設置
- [x] Google Cloud 項目已設置
- [ ] **Vertex AI Billing 已啟用** ⬅️ 等待中
- [ ] 分析已完成
- [ ] Excel 已重新導出（包含 comment_sentiment）

## 🎯 下一步行動

### 當 Billing 啟用後...

1. **立即測試**（30 秒）
   ```bash
   python3 scripts/analyze_joseph_comments.py --limit 1
   ```

2. **小批次驗證**（2 分鐘）
   ```bash
   python3 scripts/analyze_joseph_comments.py --limit 5
   ```

3. **完整處理**（15-25 分鐘）
   ```bash
   python3 scripts/analyze_joseph_comments.py
   ```

4. **重新導出 Excel**（10 秒）
   ```bash
   python3 scripts/export_joseph_to_excel.py
   ```

## 💡 提示

- 腳本會自動嘗試多個 Gemini API 區域（us-central1, us-east4, us-west1）
- 每個視頻分析間隔 10 秒，以避免配額限制
- 可以隨時 Ctrl+C 中斷，使用 `--resume` 繼續
- 重複運行腳本是安全的（會自動跳過已分析的視頻）

---

**報告生成時間**: 2026-03-11
**準備狀態**: ✅ 100% 就緒，等待 API 更新
**預計完成時間**: API 更新後 15-25 分鐘
