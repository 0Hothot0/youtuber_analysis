#!/usr/bin/env python3
"""
資料庫遷移腳本：移除 forward_number 欄位
SQLite 不支援直接 DROP COLUMN，因此需要重建表格
"""

import sqlite3
import sys


def migrate_database(db_path='youtube_analysis.db'):
    """執行資料庫遷移"""

    print("="*80)
    print("資料庫遷移：移除 forward_number 欄位")
    print("="*80)

    try:
        # 連接資料庫
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"✓ 已連接到資料庫: {db_path}")

        # 檢查舊表格記錄數
        cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data')
        old_count = cursor.fetchone()[0]
        print(f"\n舊表格記錄數: {old_count}")

        # 1. 建立新表格（不含 forward_number）
        print("\n步驟 1: 建立新表格...")
        cursor.execute('''
        CREATE TABLE Youtuber_Financial_Data_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            stock_ticker TEXT,
            like_number INTEGER,
            comment_number INTEGER,
            view_number INTEGER,
            text_type INTEGER,
            video_sentiment REAL,
            comment_sentiment REAL,
            financial_ratio REAL,
            celebrity INTEGER,
            relevancy REAL,
            published_time TEXT,
            long_term_competitiveness INTEGER,
            short_term_focus INTEGER,
            ceo_leadership_style INTEGER,
            earnings_expectation_gap REAL,
            stock_price_growth_trend REAL,
            market_demand REAL,
            market_capitalization INTEGER,
            target_price INTEGER,
            financial_health REAL,
            valuation REAL,
            policy_impact REAL,
            raw_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
        ''')
        print("✓ 新表格建立成功")

        # 2. 複製資料（排除 forward_number）
        print("\n步驟 2: 複製資料...")
        cursor.execute('''
        INSERT INTO Youtuber_Financial_Data_new
        SELECT id, video_id, stock_ticker, like_number, comment_number,
               view_number, text_type, video_sentiment, comment_sentiment,
               financial_ratio, celebrity, relevancy, published_time,
               long_term_competitiveness, short_term_focus, ceo_leadership_style,
               earnings_expectation_gap, stock_price_growth_trend, market_demand,
               market_capitalization, target_price, financial_health, valuation,
               policy_impact, raw_json, created_at, updated_at
        FROM Youtuber_Financial_Data
        ''')
        print(f"✓ 已複製 {cursor.rowcount} 筆記錄")

        # 檢查新表格記錄數
        cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data_new')
        new_count = cursor.fetchone()[0]
        print(f"新表格記錄數: {new_count}")

        if old_count != new_count:
            print(f"❌ 警告：記錄數不一致！舊表格: {old_count}, 新表格: {new_count}")
            response = input("是否繼續？(yes/no): ")
            if response.lower() != 'yes':
                print("取消遷移")
                conn.close()
                return False

        # 3. 刪除舊表格
        print("\n步驟 3: 刪除舊表格...")
        cursor.execute('DROP TABLE Youtuber_Financial_Data')
        print("✓ 舊表格已刪除")

        # 4. 重命名新表格
        print("\n步驟 4: 重命名新表格...")
        cursor.execute('ALTER TABLE Youtuber_Financial_Data_new RENAME TO Youtuber_Financial_Data')
        print("✓ 新表格已重命名為 Youtuber_Financial_Data")

        # 提交變更
        conn.commit()
        print("\n✓ 資料庫變更已提交")

        # 驗證
        print("\n驗證結果:")
        cursor.execute('PRAGMA table_info(Youtuber_Financial_Data)')
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        print(f"  表格欄位數: {len(column_names)}")
        if 'forward_number' in column_names:
            print("  ❌ 錯誤：forward_number 欄位仍然存在！")
            return False
        else:
            print("  ✓ forward_number 欄位已成功移除")

        cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data')
        final_count = cursor.fetchone()[0]
        print(f"  最終記錄數: {final_count}")

        conn.close()
        print("\n✓ 資料庫連接已關閉")

        print("\n" + "="*80)
        print("遷移成功完成！")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n❌ 遷移失敗: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False


def main():
    """主函數"""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'youtube_analysis.db'

    success = migrate_database(db_path)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
