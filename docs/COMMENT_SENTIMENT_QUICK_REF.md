# Comment Sentiment 快速參考卡

## 🎯 快速命令

### 查看當前狀態
```bash
python3 scripts/report_comment_sentiment_status.py
```

### 開始分析

```bash
# 處理 Joseph 2年期 (466筆待處理 - 最多)
python3 scripts/analyze_single_comments_improved.py --db joseph_2years

# 處理 Single 2年期 (100筆待處理)
python3 scripts/analyze_single_comments_improved.py --db single_2years

# 一次處理所有資料庫
python3 scripts/analyze_single_comments_improved.py --db all
```

### 測試模式

```bash
# 測試 3 個影片（不更新資料庫）
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --limit 3 --dry-run

# 實際測試 3 個影片
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --limit 3
```

---

## 📊 當前進度 (2026-03-12)

| 資料庫 | 待處理 | 預估時間 |
|--------|--------|----------|
| Joseph 2年期 | 466 | ~93 分鐘 |
| Joseph 3個月 | 466 | ~93 分鐘 |
| Single 2年期 | 100 | ~20 分鐘 |
| Single 3個月 | 100 | ~20 分鐘 |
| **總計** | **1,132** | **~3.8 小時** |

---

## ✨ 新功能

1. ✅ **智能重試** - 自動處理 API 失敗
2. ✅ **進度保存** - 中途中斷可續接
3. ✅ **詳細統計** - 分類錯誤類型
4. ✅ **彈性選擇** - 單一或批次處理
5. ✅ **狀態報告** - 實時追蹤進度

---

## 🔧 常用場景

### 場景 1: 首次分析
```bash
# 1. 先測試
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --limit 3

# 2. 查看結果
python3 scripts/report_comment_sentiment_status.py

# 3. 完整執行
python3 scripts/analyze_single_comments_improved.py --db joseph_2years
```

### 場景 2: 中斷後續接
```bash
# 不需要任何特殊參數，直接執行即可
python3 scripts/analyze_single_comments_improved.py --db joseph_2years
```

### 場景 3: 重新開始
```bash
python3 scripts/analyze_single_comments_improved.py --db joseph_2years --reset-progress
```

### 場景 4: 監控進度
```bash
# 在另一個終端執行
watch -n 60 python3 scripts/report_comment_sentiment_status.py
```

---

## ⚠️ 注意事項

- **API 延遲**: YouTube (0.5秒) + Gemini (10秒)
- **進度檔案**: `.comment_analysis_progress.json`
- **中斷方法**: 按 `Ctrl+C` 安全中斷

---

## 📁 相關檔案

- `scripts/analyze_single_comments_improved.py` - 主要分析工具
- `scripts/report_comment_sentiment_status.py` - 狀態報告工具
- `docs/COMMENT_SENTIMENT_GUIDE.md` - 完整使用指南
- `.comment_analysis_progress.json` - 進度檔案（自動生成）

---

## 🚀 建議執行順序

1. **查看狀態** → `report_comment_sentiment_status.py`
2. **小規模測試** → `--limit 3 --dry-run`
3. **實際測試** → `--limit 3`
4. **完整執行** → 移除 `--limit`
5. **再次查看** → `report_comment_sentiment_status.py`

---

## 📞 故障排除

| 問題 | 解決方法 |
|------|----------|
| Gemini API 失敗 | 檢查 `.env` 的 `GOOGLE_CLOUD_PROJECT` |
| YouTube 配額不足 | 等待隔天或使用 `--limit` |
| 進度檔案損壞 | 使用 `--reset-progress` |

---

## 🎉 完成確認

```bash
# 執行狀態報告
python3 scripts/report_comment_sentiment_status.py

# 確認「待處理: 0」即為完成
```
