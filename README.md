# YouTube 影片搜尋工具

使用 YouTube Data API v3 搜尋影片並取得詳細資訊，支援輸出 JSON 和 CSV 格式。

## 功能特色

- 根據關鍵字搜尋 YouTube 影片
- 取得前 10 名相關影片
- 詳細資訊包含：
  - 影片標題、連結、ID
  - 頻道名稱、頻道 ID
  - 觀看次數、按讚數、留言數
  - 發布日期、影片長度
  - 縮圖 URL（高、中、低畫質）
  - 影片描述
- 同時輸出 JSON 和 CSV 檔案

## 安裝步驟

### 1. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 2. 設定 API Key

#### 取得 YouTube Data API v3 Key

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 在左側選單點選 **APIs & Services** > **Library**
4. 搜尋 **YouTube Data API v3** 並啟用
5. 前往 **APIs & Services** > **Credentials**
6. 點選 **Create Credentials** > **API Key**
7. 複製產生的 API Key

#### 設定環境變數

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env 檔案，填入你的 API Key
# YOUTUBE_API_KEY=你的API金鑰
```

或直接在終端機設定：

```bash
export YOUTUBE_API_KEY="你的API金鑰"
```

## 使用方式

### 基本用法

```bash
python youtube_search.py "搜尋關鍵字"
```

### 範例

```bash
# 搜尋英文關鍵字
python youtube_search.py "stock market analysis"

# 搜尋中文關鍵字
python youtube_search.py "台股分析"

# 搜尋多個關鍵字
python youtube_search.py "美股 投資 教學"
```

## 輸出檔案

執行後會在 `output/` 目錄下產生兩個檔案：

- `{關鍵字}_{時間戳記}.json` - JSON 格式資料
- `{關鍵字}_{時間戳記}.csv` - CSV 格式資料（可用 Excel 開啟）

### 輸出欄位說明

| 欄位 | 說明 |
|------|------|
| video_id | 影片 ID |
| title | 影片標題 |
| url | 影片連結 |
| channel_name | 頻道名稱 |
| channel_id | 頻道 ID |
| view_count | 觀看次數 |
| like_count | 按讚數 |
| comment_count | 留言數 |
| published_at | 發布日期時間 |
| duration | 影片長度 |
| thumbnail_high | 高畫質縮圖 URL |
| thumbnail_medium | 中畫質縮圖 URL |
| thumbnail_default | 預設縮圖 URL |
| description | 影片描述 |

## 專案結構

```
youtuber_analysis/
├── youtube_search.py      # 主程式
├── requirements.txt       # Python 依賴套件
├── .env.example          # API Key 範例檔
├── .env                  # API Key 設定檔（需自行建立）
├── README.md             # 說明文件
└── output/               # 輸出目錄
    ├── *.json           # JSON 格式結果
    └── *.csv            # CSV 格式結果
```

## 注意事項

- YouTube Data API v3 有每日配額限制（預設 10,000 單位）
- 每次搜尋約消耗 100 單位配額
- 如果遇到配額不足，請等待隔天重置或申請增加配額
- API Key 請妥善保管，不要公開分享

## 常見問題

### Q: 如何增加搜尋結果數量？

修改 `youtube_search.py` 中的 `max_results` 參數（第 154 行）：

```python
video_ids = searcher.search_videos(keyword, max_results=20)  # 改為 20
```

### Q: 如何按上傳時間排序？

修改 `search_videos` 方法中的 `order` 參數（第 34 行）：

```python
order='date'  # 按日期排序（最新優先）
# 其他選項: 'rating', 'viewCount', 'title'
```

### Q: 執行時出現 API Key 錯誤？

請確認：
1. 已正確設定 `.env` 檔案
2. API Key 已複製完整
3. YouTube Data API v3 已在 Google Cloud Console 啟用

## 授權

此專案僅供學習和研究使用。
