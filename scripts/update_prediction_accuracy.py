#!/usr/bin/env python3
"""
計算 YouTuber 預測準確度分類

class = 1 (預測正確):
  1. video_sentiment > 0.1  AND  return_rate >= 5%     (看好且大漲)
  2. -0.1 <= video_sentiment <= 0.1  AND  -5% < return_rate < 5%  (中立且持平)
  3. video_sentiment < -0.1  AND  return_rate <= -5%   (看空且大跌)

class = -1 (預測錯誤):
  - 其餘所有情況
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from core.stock_price_fetcher import StockPriceFetcher

# 閾值設定
SENTIMENT_THRESHOLD = 0.1  # 情感中立範圍: ±0.1
RETURN_THRESHOLD = 0.05    # 回報率顯著變化: ±5%


def calculate_prediction_class(video_sentiment: float, return_rate: float) -> int:
    """
    根據 video_sentiment 和 return_rate 計算預測準確度分類

    Args:
        video_sentiment: 影片情感分數 (-1 到 1)
        return_rate: 實際回報率 (小數形式，如 0.05 = 5%)

    Returns:
        1: 預測正確
        -1: 預測錯誤
    """
    # 情況 1: 看好且大漲
    if video_sentiment > SENTIMENT_THRESHOLD and return_rate >= RETURN_THRESHOLD:
        return 1

    # 情況 2: 中立且持平
    if -SENTIMENT_THRESHOLD <= video_sentiment <= SENTIMENT_THRESHOLD and \
       -RETURN_THRESHOLD < return_rate < RETURN_THRESHOLD:
        return 1

    # 情況 3: 看空且大跌
    if video_sentiment < -SENTIMENT_THRESHOLD and return_rate <= -RETURN_THRESHOLD:
        return 1

    # 其餘情況: 預測錯誤
    return -1


def update_prediction_accuracy(db_path: str = 'youtube_analysis_100plus.db',
                               limit: int | None = None,
                               skip_existing: bool = True,
                               months: int = 3):
    """
    更新資料庫中的 return_rate 和 class（預測準確度）

    Args:
        db_path: 資料庫路徑
        limit: 限制處理筆數（None = 全部）
        skip_existing: 是否跳過已有 return_rate 的記錄
        months: 計算回報率的月數（預設 3 個月）
    """
    print(f"\n{'='*80}")
    print(f"更新 YouTuber 預測準確度分類")
    print(f"{'='*80}")
    print(f"資料庫: {db_path}")
    print(f"計算期間: {months} 個月")
    print(f"情感閾值: ±{SENTIMENT_THRESHOLD}")
    print(f"回報率閾值: ±{RETURN_THRESHOLD*100}%")
    print(f"{'='*80}\n")

    # 連接資料庫
    db = DatabaseManager(db_path)
    db.connect()

    # 初始化股價抓取器
    fetcher = StockPriceFetcher()

    # 查詢需要更新的記錄
    if skip_existing:
        condition = "WHERE return_rate IS NULL OR return_rate = 0"
    else:
        condition = ""

    db.cursor.execute(f"""
        SELECT
            id,
            video_id,
            stock_ticker,
            published_time,
            video_sentiment,
            return_rate,
            class
        FROM Youtuber_Financial_Data
        {condition}
        ORDER BY published_time DESC
        {f'LIMIT {limit}' if limit else ''}
    """)

    records = db.cursor.fetchall()
    total = len(records)

    if total == 0:
        print("✓ 沒有需要更新的記錄")
        db.close()
        return

    print(f"找到 {total} 筆需要更新的記錄\n")

    # 統計變數
    success_count = 0
    error_count = 0
    skipped_count = 0

    class_1_count = 0  # 預測正確
    class_minus1_count = 0  # 預測錯誤

    # 逐筆處理
    for idx, row in enumerate(records, 1):
        record_id = row['id']
        video_id = row['video_id']
        ticker = row['stock_ticker']
        published_time = row['published_time']
        video_sentiment = row['video_sentiment']

        print(f"[{idx}/{total}] 處理記錄 #{record_id}")
        print(f"  影片: {video_id}")
        print(f"  股票: {ticker}")
        print(f"  發布: {published_time}")
        print(f"  情感: {video_sentiment:.2f}", end="")

        # 情感分類標籤
        if video_sentiment > SENTIMENT_THRESHOLD:
            sentiment_label = "正面"
        elif video_sentiment < -SENTIMENT_THRESHOLD:
            sentiment_label = "負面"
        else:
            sentiment_label = "中立"
        print(f" ({sentiment_label})")

        # 檢查必要欄位
        if not ticker:
            print(f"  ⚠️ 跳過: 無股票代碼")
            skipped_count += 1
            continue

        if not published_time:
            print(f"  ⚠️ 跳過: 無發布時間")
            skipped_count += 1
            continue

        if video_sentiment is None:
            print(f"  ⚠️ 跳過: 無情感分數")
            skipped_count += 1
            continue

        # 計算回報率
        try:
            result = fetcher.calculate_custom_return(
                ticker,
                published_time,
                months=months,
                threshold=RETURN_THRESHOLD
            )

            if result:
                return_rate, _ = result  # 忽略舊的 class 計算

                # 使用新邏輯計算 class
                classification = calculate_prediction_class(video_sentiment, return_rate)

                print(f"  ✓ 回報率: {return_rate*100:+.2f}%", end="")

                # 回報率分類標籤
                if return_rate >= RETURN_THRESHOLD:
                    return_label = "大漲"
                elif return_rate <= -RETURN_THRESHOLD:
                    return_label = "大跌"
                else:
                    return_label = "持平"
                print(f" ({return_label})")

                print(f"  ✓ 預測: {'✓ 正確' if classification == 1 else '✗ 錯誤'} (class={classification})")

                # 更新資料庫
                db.cursor.execute("""
                    UPDATE Youtuber_Financial_Data
                    SET return_rate = ?,
                        class = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (return_rate, classification, record_id))
                db.conn.commit()

                success_count += 1
                if classification == 1:
                    class_1_count += 1
                else:
                    class_minus1_count += 1

            else:
                print(f"  ✗ 計算失敗: 無法取得股價資料")
                error_count += 1

        except Exception as e:
            print(f"  ✗ 錯誤: {str(e)}")
            error_count += 1

        # 進度提示
        if idx % 10 == 0:
            print(f"\n--- 進度: {idx}/{total} ({idx*100//total}%) ---")
            print(f"成功: {success_count}, 錯誤: {error_count}, 略過: {skipped_count}\n")

    # 最終統計
    print(f"\n{'='*80}")
    print("更新完成！")
    print(f"{'='*80}")
    print(f"  總計: {total}")
    print(f"  成功: {success_count}")
    print(f"  錯誤: {error_count}")
    print(f"  略過: {skipped_count}")
    print(f"\n預測準確度統計:")
    print(f"  預測正確 (class=1):  {class_1_count} ({class_1_count*100/success_count:.1f}%)" if success_count > 0 else "  無資料")
    print(f"  預測錯誤 (class=-1): {class_minus1_count} ({class_minus1_count*100/success_count:.1f}%)" if success_count > 0 else "")
    print(f"{'='*80}\n")

    # 顯示更新後的資料樣本
    if success_count > 0:
        print(f"更新後的資料樣本（前 10 筆）:\n")
        db.cursor.execute("""
            SELECT
                stock_ticker,
                video_sentiment,
                return_rate,
                class,
                published_time
            FROM Youtuber_Financial_Data
            WHERE return_rate IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 10
        """)

        print(f"{'股票':<8} {'情感':<8} {'回報率':<10} {'class':<6} {'發布日期'}")
        print("-" * 60)

        for row in db.cursor.fetchall():
            ticker = row['stock_ticker'] or 'N/A'
            sentiment = f"{row['video_sentiment']:.2f}" if row['video_sentiment'] is not None else 'N/A'
            return_val = f"{row['return_rate']*100:+.2f}%" if row['return_rate'] is not None else 'N/A'
            class_val = row['class'] if row['class'] is not None else 'N/A'
            date = row['published_time'][:10] if row['published_time'] else 'N/A'
            print(f"{ticker:<8} {sentiment:<8} {return_val:<10} {class_val:<6} {date}")

    # 整體統計
    print(f"\n{'='*80}")
    print("資料庫整體統計")
    print(f"{'='*80}")

    db.cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END) as correct,
            SUM(CASE WHEN class = -1 THEN 1 ELSE 0 END) as incorrect,
            AVG(return_rate) as avg_return,
            AVG(video_sentiment) as avg_sentiment
        FROM Youtuber_Financial_Data
        WHERE return_rate IS NOT NULL
    """)

    stats = db.cursor.fetchone()
    if stats and stats['total'] > 0:
        accuracy = stats['correct'] * 100 / stats['total']
        print(f"  已計算記錄: {stats['total']}")
        print(f"  預測正確:   {stats['correct']} ({accuracy:.1f}%)")
        print(f"  預測錯誤:   {stats['incorrect']} ({100-accuracy:.1f}%)")
        print(f"  平均回報率: {stats['avg_return']*100:+.2f}%")
        print(f"  平均情感:   {stats['avg_sentiment']:.2f}")
    else:
        print("  無資料")

    print(f"{'='*80}\n")

    db.close()


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="計算 YouTuber 預測準確度分類（基於情感分析與實際回報率）"
    )

    parser.add_argument(
        '--db',
        default='youtube_analysis_100plus.db',
        help='資料庫路徑（預設: youtube_analysis_100plus.db）'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='限制處理筆數（預設: 全部）'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='強制重新計算所有記錄（包含已有值的）'
    )

    parser.add_argument(
        '--months',
        type=int,
        default=3,
        help='計算回報率的月數（預設: 3）'
    )

    args = parser.parse_args()

    # 確認操作
    if args.force:
        response = input(f"\n⚠️  將強制重新計算所有記錄，是否繼續？(y/N): ")
        if response.lower() != 'y':
            print("操作已取消")
            sys.exit(0)

    # 執行更新
    update_prediction_accuracy(
        db_path=args.db,
        limit=args.limit,
        skip_existing=not args.force,
        months=args.months
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 使用者中斷操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
