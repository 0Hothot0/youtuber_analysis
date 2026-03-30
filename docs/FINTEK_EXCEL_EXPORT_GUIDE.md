# Fin Tek Excel 導出說明

**創建日期**: 2026-03-23
**狀態**: ✅ 完成

---

## 文件概覽

成功導出 **5 個時間周期** 的數據，每個周期包含 **3 個版本**：

| 時間周期 | Clean | Train | Test | 總計 |
|---------|-------|-------|------|------|
| 1 個月  | ✓ | ✓ | ✓ | 3 檔 |
| 3 個月  | ✓ | ✓ | ✓ | 3 檔 |
| 6 個月  | ✓ | ✓ | ✓ | 3 檔 |
| 1 年    | ✓ | ✓ | ✓ | 3 檔 |
| 2 年    | ✓ | ✓ | ✓ | 3 檔 |

**總文件數**: 15 個 Excel 文件
**輸出目錄**: `exports/fin_tek/`

---

## 文件說明

### 1. Clean 版本 (`*_clean.xlsx`)

**用途**: 完整數據集，已標準化

- **記錄數**: 114 筆
- **特點**: 使用完整數據的統計數據進行標準化
- **適用**: 數據分析、可視化、完整評估

### 2. Train 版本 (`*_train.xlsx`)

**用途**: 訓練集 (80%)

- **記錄數**: 91 筆
- **特點**: Stratified split（保持 class 比例）
- **標準化**: 使用 Train set 自身的統計數據
- **適用**: 模型訓練

### 3. Test 版本 (`*_test.xlsx`)

**用途**: 測試集 (20%)

- **記錄數**: 23 筆
- **特點**: 使用與 Train set **相同的 StandardScaler**
- **重要**: 避免數據洩漏！
- **適用**: 模型評估、驗證

---

## 數據標準化

### 標準化欄位

對以下 4 個欄位進行 **Z-score 標準化**：

```python
COLUMNS_TO_STANDARDIZE = [
    'like_number',      # 按讚數
    'comment_number',   # 留言數
    'view_number',      # 觀看數
    'during'            # 評估期間天數
]
```

### 標準化公式

```
標準化值 = (原始值 - 平均值) / 標準差
```

**結果**: mean ≈ 0, std ≈ 1

### 為何標準化這些欄位？

1. **like_number, comment_number, view_number**:
   - 數值範圍差異大（幾千到幾十萬）
   - 標準化後讓機器學習模型更容易收斂

2. **during**:
   - 不同時間周期的天數不同
   - 標準化後便於跨周期比較

---

## 數據切分策略

### Stratified Split

**方法**: `train_test_split(stratify=df['class'])`

**優點**:
- Train 和 Test 保持相同的 class 比例
- 避免樣本不平衡問題

### 實際比例

| 時間周期 | Train (Class 1) | Test (Class 1) | Train (Class -1) | Test (Class -1) |
|---------|----------------|---------------|-----------------|----------------|
| 1 個月  | ~57% | ~57% | ~43% | ~43% |
| 3 個月  | ~49% | ~49% | ~51% | ~51% |
| 6 個月  | ~45% | ~45% | ~55% | ~55% |
| 1 年    | ~64% | ~64% | ~36% | ~36% |
| 2 年    | ~59% | ~59% | ~41% | ~41% |

**Random Seed**: 42 (可重現結果)

---

## 完整欄位列表 (32 個)

### 識別欄位
1. `id` - 記錄 ID
2. `video_uuid` - 影片唯一識別碼
3. `video_id` - YouTube 影片 ID
4. `stock_ticker` - 股票代碼

### 影片資訊
5. `title` - 影片標題
6. `published_time` - 發布時間
7. `view_number` - 觀看數 (已標準化)
8. `like_number` - 按讚數 (已標準化)
9. `comment_number` - 留言數 (已標準化)
10. `youtuber` - YouTuber 名稱

### 情緒分析 (Gemini AI)
11. `video_sentiment` - 影片情緒 (-1 到 1)
12. `comment_sentiment` - 留言情緒 (目前為 0)

### 財務指標 (17 個)
13. `stock_price_mentioned` - 提到股價 (0/1)
14. `revenue_growth` - 營收增長
15. `earnings_growth` - 盈利增長
16. `profit_margin` - 利潤率
17. `debt_level` - 債務水平
18. `market_position` - 市場地位
19. `competitive_advantage` - 競爭優勢
20. `growth_potential` - 增長潛力
21. `valuation_concern` - 估值擔憂
22. `regulatory_risk` - 監管風險
23. `market_trend_alignment` - 市場趨勢對齊
24. `innovation_factor` - 創新因子
25. `management_quality` - 管理質量
26. `earnings_surprise` - 盈利驚喜
27. `analyst_rating` - 分析師評級
28. `technical_indicator` - 技術指標
29. `raw_json` - 原始 JSON

### 計算欄位
30. `return_rate` - 實際回報率
31. `during` - 評估期間天數 (已標準化)
32. `class` - 預測準確性 (1=正確, -1=錯誤) **[Target Variable]**

---

## 使用範例

### Python - 讀取 Excel

```python
import pandas as pd

# 讀取訓練集
train_df = pd.read_excel('exports/fin_tek/fintek_1year_train.xlsx')

# 分離特徵和標籤
X_train = train_df.drop('class', axis=1)
y_train = train_df['class']

# 讀取測試集
test_df = pd.read_excel('exports/fin_tek/fintek_1year_test.xlsx')
X_test = test_df.drop('class', axis=1)
y_test = test_df['class']
```

### 機器學習訓練

```python
from sklearn.ensemble import RandomForestClassifier

# 選擇數值型特徵（已標準化）
numeric_features = [
    'video_sentiment',
    'like_number', 'comment_number', 'view_number',
    'stock_price_mentioned', 'revenue_growth', 'earnings_growth',
    # ... 其他財務指標
    'return_rate', 'during'
]

X_train_numeric = train_df[numeric_features]
X_test_numeric = test_df[numeric_features]

# 訓練模型
model = RandomForestClassifier(random_state=42)
model.fit(X_train_numeric, y_train)

# 評估
accuracy = model.score(X_test_numeric, y_test)
print(f'測試準確率: {accuracy:.2%}')
```

---

## 數據質量檢查

### ✅ 驗證通過

- [x] 所有欄位無空值（return_rate, class, during）
- [x] 標準化統計正確（mean ≈ 0, std ≈ 1）
- [x] Train/Test 使用相同的 StandardScaler
- [x] Class 分佈保持 Stratified
- [x] 檔案大小合理（~30KB clean, ~26KB train, ~11KB test）

### 每個時間周期統計

| 周期 | 記錄數 | Class 1 | Class -1 | 準確率 |
|------|--------|---------|----------|--------|
| 1月  | 114 | 65 (57.0%) | 49 (43.0%) | 57.02% |
| 3月  | 114 | 56 (49.1%) | 58 (50.9%) | 49.12% |
| 6月  | 114 | 51 (44.7%) | 63 (55.3%) | 44.74% |
| 1年  | 114 | 73 (64.0%) | 41 (36.0%) | **64.04%** ⭐ |
| 2年  | 114 | 67 (58.8%) | 47 (41.2%) | 58.77% |

---

## 注意事項

### ⚠️ 重要提醒

1. **Train/Test Scaler 一致性**
   - Test set 必須使用 Train set 的 StandardScaler
   - 已在腳本中正確實現
   - 避免數據洩漏

2. **comment_sentiment 欄位**
   - 目前所有記錄為 0
   - 未來需要進行留言情緒分析

3. **class 欄位的含義**
   - **Class 1**: Fin Tek 預測正確（sentiment 與 return_rate 方向一致）
   - **Class -1**: Fin Tek 預測錯誤（sentiment 與 return_rate 方向不一致）
   - **閾值**: ±5% return_rate

4. **不同時間周期的 class**
   - 每個數據庫的 class 都是**獨立計算**的
   - 同一支股票在不同周期可能有不同的 class
   - 這是正常的！(例如：短期正確，長期錯誤)

---

## 文件清單

```
exports/fin_tek/
├── fintek_1month_clean.xlsx    (30 KB) - 1個月完整數據
├── fintek_1month_train.xlsx    (26 KB) - 1個月訓練集
├── fintek_1month_test.xlsx     (11 KB) - 1個月測試集
├── fintek_3months_clean.xlsx   (30 KB) - 3個月完整數據
├── fintek_3months_train.xlsx   (26 KB) - 3個月訓練集
├── fintek_3months_test.xlsx    (11 KB) - 3個月測試集
├── fintek_6months_clean.xlsx   (30 KB) - 6個月完整數據
├── fintek_6months_train.xlsx   (26 KB) - 6個月訓練集
├── fintek_6months_test.xlsx    (11 KB) - 6個月測試集
├── fintek_1year_clean.xlsx     (30 KB) - 1年完整數據
├── fintek_1year_train.xlsx     (26 KB) - 1年訓練集
├── fintek_1year_test.xlsx      (11 KB) - 1年測試集
├── fintek_2years_clean.xlsx    (30 KB) - 2年完整數據
├── fintek_2years_train.xlsx    (26 KB) - 2年訓練集
└── fintek_2years_test.xlsx     (11 KB) - 2年測試集
```

---

## 後續分析建議

### 1. 預測模型開發
- 使用 1 年數據（準確率最高 64.04%）
- 嘗試不同算法：Random Forest, XGBoost, Neural Network
- 特徵工程：組合財務指標

### 2. 特徵重要性分析
- 哪些財務指標最能預測準確性？
- video_sentiment 的權重如何？
- view_number 是否影響預測質量？

### 3. 跨時間周期分析
- 為何 1 年預測最準確？
- 6 個月為何最差？
- 短期 vs 長期預測模式差異

### 4. 與其他 YouTuber 對比
- Fin Tek vs Joseph Hogue vs Tom Nash
- 誰的預測風格更穩定？
- 哪個時間周期各自擅長？

---

## 技術規格

- **Python 版本**: 3.12+
- **依賴套件**:
  - pandas
  - openpyxl
  - scikit-learn
  - numpy
- **腳本**: `scripts/export_fintek_excel_standardized.py`
- **創建時間**: 2026-03-23

---

**文檔版本**: 1.0
**最後更新**: 2026-03-23
