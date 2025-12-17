#!/usr/bin/env python3
"""
資料庫遷移腳本：移除重複影片記錄並添加 UNIQUE 約束
解決 Race Condition 導致的重複插入問題
"""

import sqlite3
import sys


def migrate_database(db_path='youtube_analysis.db'):
    """執行資料庫遷移：清理重複並重建表格"""

    print("="*80)
    print("資料庫遷移：移除重複影片並添加 UNIQUE 約束")
    print("="*80)

    try:
        # 連接資料庫
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"✓ 已連接到資料庫: {db_path}")

        # 檢查舊表格統計
        cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data')
        old_total = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(DISTINCT video_id) as count FROM Youtuber_Financial_Data')
        unique_count = cursor.fetchone()[0]

        duplicate_count = old_total - unique_count

        print(f"\n原始資料統計:")
        print(f"  總記錄數: {old_total}")
        print(f"  不重複 video_id: {unique_count}")
        print(f"  重複記錄數: {duplicate_count}")

        if duplicate_count == 0:
            print("\n✓ 沒有重複記錄，無需清理")
            conn.close()
            return True

        # 步驟 1: 刪除重複記錄（保留 id 最小的）
        print("\n步驟 1: 刪除重複記錄...")
        cursor.execute('''
            DELETE FROM Youtuber_Financial_Data
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM Youtuber_Financial_Data
                GROUP BY video_id
            )
        ''')
        deleted_count = cursor.rowcount
        print(f"✓ 已刪除 {deleted_count} 筆重複記錄")

        # 驗證刪除後的記錄數
        cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data')
        after_delete = cursor.fetchone()[0]
        print(f"  刪除後記錄數: {after_delete}")

        # 步驟 2: 建立新表格（含 UNIQUE 約束）
        print("\n步驟 2: 建立新表格（含 UNIQUE 約束）...")
        cursor.execute('''
        CREATE TABLE Youtuber_Financial_Data_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL UNIQUE,
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
        print("✓ 新表格建立成功（含 UNIQUE 約束）")

        # 步驟 3: 複製資料
        print("\n步驟 3: 複製資料到新表格...")
        cursor.execute('''
        INSERT INTO Youtuber_Financial_Data_new
        SELECT * FROM Youtuber_Financial_Data
        ''')
        copied_count = cursor.rowcount
        print(f"✓ 已複製 {copied_count} 筆記錄")

        # 驗證新表格記錄數
        cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data_new')
        new_count = cursor.fetchone()[0]
        print(f"  新表格記錄數: {new_count}")

        if new_count != after_delete:
            print(f"❌ 警告：記錄數不一致！舊表: {after_delete}, 新表: {new_count}")
            response = input("是否繼續？(yes/no): ")
            if response.lower() != 'yes':
                print("取消遷移")
                conn.rollback()
                conn.close()
                return False

        # 步驟 4: 刪除舊表格
        print("\n步驟 4: 刪除舊表格...")
        cursor.execute('DROP TABLE Youtuber_Financial_Data')
        print("✓ 舊表格已刪除")

        # 步驟 5: 重命名新表格
        print("\n步驟 5: 重命名新表格...")
        cursor.execute('ALTER TABLE Youtuber_Financial_Data_new RENAME TO Youtuber_Financial_Data')
        print("✓ 新表格已重命名為 Youtuber_Financial_Data")

        # 提交變更
        conn.commit()
        print("\n✓ 資料庫變更已提交")

        # 驗證
        print("\n驗證結果:")
        cursor.execute('PRAGMA table_info(Youtuber_Financial_Data)')
        columns = cursor.fetchall()

        # 檢查 video_id 是否有 UNIQUE 約束
        has_unique = False
        for col in columns:
            if col[1] == 'video_id':
                # SQLite PRAGMA table_info 不會顯示 UNIQUE
                # 需要查詢 sqlite_master
                cursor.execute('''
                    SELECT sql FROM sqlite_master
                    WHERE type='table' AND name='Youtuber_Financial_Data'
                ''')
                create_sql = cursor.fetchone()[0]
                if 'UNIQUE' in create_sql and 'video_id' in create_sql:
                    has_unique = True
                break

        if has_unique:
            print("  ✓ video_id 欄位已有 UNIQUE 約束")
        else:
            print("  ❌ 警告：video_id 欄位可能沒有 UNIQUE 約束")

        cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data')
        final_count = cursor.fetchone()[0]
        print(f"  最終記錄數: {final_count}")

        cursor.execute('SELECT COUNT(DISTINCT video_id) as count FROM Youtuber_Financial_Data')
        final_unique = cursor.fetchone()[0]
        print(f"  不重複 video_id: {final_unique}")

        if final_count == final_unique:
            print("  ✓ 確認無重複記錄")
        else:
            print(f"  ❌ 仍有 {final_count - final_unique} 筆重複記錄")

        conn.close()
        print("\n✓ 資料庫連接已關閉")

        print("\n" + "="*80)
        print("遷移成功完成！")
        print(f"清理了 {deleted_count} 筆重複記錄")
        print(f"最終保留 {final_count} 筆不重複記錄")
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
