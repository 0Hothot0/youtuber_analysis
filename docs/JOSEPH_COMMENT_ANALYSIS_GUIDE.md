# Joseph Hogue 評論情感分析指南

## 概述

這個文檔說明如何為 Joseph Hogue 的數據庫分析 YouTube 評論情感。

## 準備工作

### 1. 確認數據庫已創建

```bash
ls -lh youtube_analysis_*single_joseph.db
```

應該看到：
- `youtube_analysis_2years_single_joseph.db` (2.1M)
- `youtube_analysis_3months_single_joseph.db` (1.9M)

### 2. 確認環境變量

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('YOUTUBE_API_KEY:', '已設置' if os.getenv('YOUTUBE_API_KEY') else '❌未設置')
print('GOOGLE_CLOUD_PROJECT:', '已設置' if os.getenv('GOOGLE_CLOUD_PROJECT') else '❌未設置')
"
```

## 使用方法

### 基本命令

```bash
# 分析所有數據庫（2years + 3months）
python3 scripts/analyze_joseph_comments.py

# 只分析 2years 數據庫
python3 scripts/analyze_joseph_comments.py --database 2years

# 只分析 3months 數據庫
python3 scripts/analyze_joseph_comments.py --database 3months
```

### 測試模式

建議先進行 dry-run 測試，確保 API 連接正常：

```bash
# 測試模式：分析前 2 個視頻（不更新數據庫）
python3 scripts/analyze_joseph_comments.py --limit 2 --dry-run
```

### 小批次測試

```bash
# 先處理 5 個視頻作為測試
python3 scripts/analyze_joseph_comments.py --limit 5
```

### 完整批次處理

```bash
# 處理所有待分析的視頻（約 92 個唯一視頻）
python3 scripts/analyze_joseph_comments.py
```

## 數據統計

### 當前狀態

- **2years 數據庫**: 466 條記錄，約 92 個唯一視頻
- **3months 數據庫**: 466 條記錄，約 31 個唯一視頻
- **comment_sentiment**: 全部為 0（待分析）

### 預計時間

- 每個視頻約需 10-15 秒（抓取評論 + Gemini 分析 + API 延遲）
- 92 個唯一視頻約需 **15-25 分鐘**

## API 配額考慮

### YouTube Data API v3

- **每日限額**: 10,000 units（默認）
- **comments.list**: 約 1 unit per request
- **92 個視頻**: 約 92 units（配額充足）

### Google Vertex AI Gemini

- 使用 `gemini-1.5-flash-001` 模型
- 腳本會自動嘗試多個區域：
  - us-central1（首選）
  - us-east4
  - us-west1
- 每次 API 調用間隔 10 秒

## 常見情況處理

### 1. 評論已關閉

```
留言已關閉 - 返回 None
```

→ 數據庫中該視頻的 `comment_sentiment` 將設為 `NULL`

### 2. 無評論

```
無留言 - 返回 0.0
```

→ 數據庫中該視頻的 `comment_sentiment` 將設為 `0.0`

### 3. 有評論

```
找到 25 則留言 (1234 字符)
情緒分數: 0.645
```

→ 數據庫中該視頻的 `comment_sentiment` 將設為計算出的分數（-1 到 +1）

## 中斷處理

如果分析過程中被中斷（Ctrl+C），可以使用 `--resume` 繼續：

```bash
python3 scripts/analyze_joseph_comments.py --resume
```

腳本會自動跳過已分析的視頻。

## 驗證結果

### 查看分析進度

```bash
python3 -c "
import sqlite3

for db in ['youtube_analysis_2years_single_joseph.db', 'youtube_analysis_3months_single_joseph.db']:
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT video_id) as unique_videos,
            SUM(CASE WHEN comment_sentiment = 0 THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN comment_sentiment IS NULL THEN 1 ELSE 0 END) as no_comments,
            SUM(CASE WHEN comment_sentiment > 0 OR comment_sentiment < 0 THEN 1 ELSE 0 END) as analyzed
        FROM Youtuber_Financial_Data
    ''')

    result = cursor.fetchone()
    print(f'\n{db}:')
    print(f'  總記錄: {result[0]}')
    print(f'  唯一視頻: {result[1]}')
    print(f'  待分析: {result[2]}')
    print(f'  已分析: {result[4]}')
    print(f'  無評論: {result[3]}')

    conn.close()
"
```

### 查看情緒分數分佈

```bash
python3 -c "
import sqlite3

conn = sqlite3.connect('youtube_analysis_2years_single_joseph.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT
        AVG(comment_sentiment) as avg,
        MIN(comment_sentiment) as min,
        MAX(comment_sentiment) as max,
        COUNT(CASE WHEN comment_sentiment > 0 THEN 1 END) as positive,
        COUNT(CASE WHEN comment_sentiment < 0 THEN 1 END) as negative,
        COUNT(CASE WHEN comment_sentiment = 0 THEN 1 END) as neutral
    FROM Youtuber_Financial_Data
    WHERE comment_sentiment IS NOT NULL
''')

result = cursor.fetchone()
print('\n情緒分數統計:')
print(f'  平均值: {result[0]:.3f}' if result[0] else '  無數據')
print(f'  最小值: {result[1]:.3f}' if result[1] else '  無數據')
print(f'  最大值: {result[2]:.3f}' if result[2] else '  無數據')
print(f'  正面: {result[3]}')
print(f'  負面: {result[4]}')
print(f'  中性: {result[5]}')

conn.close()
"
```

## 重新導出 Excel

分析完成後，重新導出 Excel 文件以包含最新的 comment_sentiment 數據：

```bash
python3 scripts/export_joseph_to_excel.py
```

新的 Excel 文件將包含更新後的 comment_sentiment 字段。

## 故障排除

### 錯誤：無法找到可用的 Gemini 配置

**原因**: Vertex AI API 配額不足或未啟用

**解決方案**:
1. 檢查 Google Cloud Console 中的 Vertex AI API 狀態
2. 確認項目有足夠的配額
3. 等待配額重置（通常每分鐘重置）
4. 嘗試使用 `--limit 1` 測試單個視頻

### 錯誤：Rate limit exceeded (YouTube API)

**解決方案**:
1. 檢查 YouTube API 配額使用情況
2. 等待配額重置（每日重置）
3. 使用 `--limit` 參數分批處理

### 第一個視頻就失敗

腳本會在第一個視頻失敗時立即停止，避免浪費配額。請檢查：
1. API 密鑰是否正確
2. 網絡連接是否正常
3. API 配額是否充足

## 最佳實踐

1. **先測試**: 使用 `--limit 2 --dry-run` 測試
2. **小批次**: 先用 `--limit 5` 處理少量視頻
3. **監控配額**: 定期檢查 API 配額使用情況
4. **分批處理**: 如果視頻很多，可以分多次處理
5. **保存結果**: 每批處理完後，運行驗證腳本檢查結果

## 示例工作流程

```bash
# 步驟 1: 測試連接（dry-run）
python3 scripts/analyze_joseph_comments.py --limit 1 --dry-run

# 步驟 2: 小批次測試（實際更新）
python3 scripts/analyze_joseph_comments.py --limit 5

# 步驟 3: 驗證結果
python3 -c "import sqlite3; conn = sqlite3.connect('youtube_analysis_2years_single_joseph.db'); \
cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM Youtuber_Financial_Data WHERE comment_sentiment != 0'); \
print(f'已分析: {cursor.fetchone()[0]} 條'); conn.close()"

# 步驟 4: 完整批次處理
python3 scripts/analyze_joseph_comments.py

# 步驟 5: 重新導出 Excel
python3 scripts/export_joseph_to_excel.py
```

## 注意事項

- ⚠️ **當前 API 未更新時，會提示等待**: 腳本會顯示提示信息，要求 API 更新後再運行
- ✅ **自動跳過已分析視頻**: 重複運行腳本是安全的
- ✅ **同時更新兩個數據庫**: 一次運行會更新 2years 和 3months 數據庫
- ✅ **支持中斷恢復**: 使用 Ctrl+C 中斷後可以繼續

## 相關文件

- 腳本: `scripts/analyze_joseph_comments.py`
- 數據庫: `youtube_analysis_*_single_joseph.db`
- 導出腳本: `scripts/export_joseph_to_excel.py`
- Excel 輸出: `exports/youtube_analysis_*_single_joseph.xlsx`
