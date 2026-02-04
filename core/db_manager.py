#!/usr/bin/env python3
"""
資料庫管理模組
管理 SQLite 資料庫操作，包含建立資料表、CRUD 操作等
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class DatabaseManager:
    """SQLite 資料庫管理類別"""

    def __init__(self, db_path: str = "youtube_analysis.db"):
        """初始化資料庫連接"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """連接到資料庫"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # 允許使用欄位名稱存取
        self.cursor = self.conn.cursor()
        print(f"✓ 已連接到資料庫: {self.db_path}")

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            print("✓ 資料庫連接已關閉")

    def create_tables(self):
        """建立所有資料表"""
        print("\n建立資料表...")

        # 資料表 1: youtubers (YouTuber 清單)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtubers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        print("✓ 建立 youtubers 資料表")

        # 資料表 2: search_tags (搜尋標籤)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        print("✓ 建立 search_tags 資料表")

        # 資料表 3: videos (YouTube 影片資料)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                channel_name TEXT,
                channel_id TEXT,
                description TEXT,
                published_at TEXT,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                duration TEXT,
                thumbnail_default TEXT,
                thumbnail_medium TEXT,
                thumbnail_high TEXT,
                search_keyword TEXT,
                youtuber_id INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (youtuber_id) REFERENCES youtubers(id)
            )
        """)
        print("✓ 建立 videos 資料表")

        # 建立索引
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_channel_id
            ON videos(channel_id)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_published_at
            ON videos(published_at)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_youtuber_id
            ON videos(youtuber_id)
        """)

        # 資料表 4: Youtuber_Financial_Data (Gemini 分析結果)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Youtuber_Financial_Data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_uuid TEXT NOT NULL,
                video_id TEXT NOT NULL,
                stock_ticker TEXT,
                like_number INTEGER,
                comment_number INTEGER,
                view_number INTEGER,
                text_type INTEGER,
                video_sentiment REAL,
                comment_sentiment REAL DEFAULT 0,
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
                return_rate REAL DEFAULT NULL,
                class INTEGER DEFAULT NULL,
                youtuber TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(video_id, stock_ticker),
                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            )
        """)
        print("✓ 建立 Youtuber_Financial_Data 資料表")

        self.conn.commit()
        print("\n✓ 所有資料表建立完成\n")

    # ==================== YouTuber 操作 ====================

    def insert_youtuber(self, name: str) -> Optional[int]:
        """新增 YouTuber"""
        try:
            self.cursor.execute(
                "INSERT INTO youtubers (name) VALUES (?)",
                (name,)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # 如果已存在，返回現有ID
            self.cursor.execute(
                "SELECT id FROM youtubers WHERE name = ?",
                (name,)
            )
            result = self.cursor.fetchone()
            return result[0] if result else None

    def get_all_youtubers(self) -> List[Dict[str, Any]]:
        """取得所有 YouTuber"""
        self.cursor.execute("SELECT * FROM youtubers ORDER BY id")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    # ==================== 搜尋標籤操作 ====================

    def insert_tag(self, tag: str) -> Optional[int]:
        """新增搜尋標籤"""
        try:
            self.cursor.execute(
                "INSERT INTO search_tags (tag) VALUES (?)",
                (tag.strip(),)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # 如果已存在，返回現有ID
            self.cursor.execute(
                "SELECT id FROM search_tags WHERE tag = ?",
                (tag.strip(),)
            )
            result = self.cursor.fetchone()
            return result[0] if result else None

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """取得所有搜尋標籤"""
        self.cursor.execute("SELECT * FROM search_tags ORDER BY id")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    # ==================== 影片操作 ====================

    def insert_video(self, video_data: Dict[str, Any]) -> Optional[int]:
        """新增影片資料"""
        try:
            self.cursor.execute("""
                INSERT INTO videos (
                    video_id, url, title, channel_name, channel_id,
                    description, published_at, view_count, like_count,
                    comment_count, duration, thumbnail_default,
                    thumbnail_medium, thumbnail_high, search_keyword, youtuber_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                video_data.get('video_id'),
                video_data.get('url'),
                video_data.get('title'),
                video_data.get('channel_name'),
                video_data.get('channel_id'),
                video_data.get('description'),
                video_data.get('published_at'),
                video_data.get('view_count', 0),
                video_data.get('like_count', 0),
                video_data.get('comment_count', 0),
                video_data.get('duration'),
                video_data.get('thumbnail_default'),
                video_data.get('thumbnail_medium'),
                video_data.get('thumbnail_high'),
                video_data.get('search_keyword'),
                video_data.get('youtuber_id')
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            print(f"⚠️ 影片已存在: {video_data.get('video_id')}")
            return None

    def get_video_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """根據 video_id 取得影片"""
        self.cursor.execute(
            "SELECT * FROM videos WHERE video_id = ?",
            (video_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_videos_by_youtuber(self, youtuber_id: int) -> List[Dict[str, Any]]:
        """取得特定 YouTuber 的所有影片"""
        self.cursor.execute(
            "SELECT * FROM videos WHERE youtuber_id = ? ORDER BY published_at DESC",
            (youtuber_id,)
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    # ==================== Gemini 分析結果操作 ====================

    def insert_financial_data(self, data: Dict[str, Any]) -> Optional[int]:
        """新增 Gemini 財務分析資料"""
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO Youtuber_Financial_Data (
                    video_uuid, video_id, stock_ticker, like_number, comment_number,
                    view_number, text_type, video_sentiment,
                    comment_sentiment, financial_ratio, celebrity, relevancy,
                    published_time, long_term_competitiveness, short_term_focus,
                    ceo_leadership_style, earnings_expectation_gap,
                    stock_price_growth_trend, market_demand, market_capitalization,
                    target_price, financial_health, valuation, policy_impact, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('video_uuid'),
                data.get('video_id'),
                data.get('stock_ticker'),
                data.get('like_number'),
                data.get('comment_number'),
                data.get('view_number'),
                data.get('text_type'),
                data.get('video_sentiment'),
                data.get('comment_sentiment', 0),
                data.get('financial_ratio'),
                data.get('celebrity'),
                data.get('relevancy'),
                data.get('published_time'),
                data.get('long_term_competitiveness'),
                data.get('short_term_focus'),
                data.get('ceo_leadership_style'),
                data.get('earnings_expectation_gap'),
                data.get('stock_price_growth_trend'),
                data.get('market_demand'),
                data.get('market_capitalization'),
                data.get('target_price'),
                data.get('financial_health'),
                data.get('valuation'),
                data.get('policy_impact'),
                data.get('raw_json')
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"❌ 新增財務資料失敗: {str(e)}")
            return None

    def get_financial_data_by_video(self, video_id: str) -> List[Dict[str, Any]]:
        """取得特定影片的財務分析資料"""
        self.cursor.execute(
            "SELECT * FROM Youtuber_Financial_Data WHERE video_id = ?",
            (video_id,)
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_financial_data_by_uuid(self, video_uuid: str) -> List[Dict[str, Any]]:
        """根據 UUID 取得所有分析記錄（同一影片的多個股票）"""
        self.cursor.execute(
            "SELECT * FROM Youtuber_Financial_Data WHERE video_uuid = ?",
            (video_uuid,)
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_pending_video_uuids(self) -> List[Dict[str, Any]]:
        """取得需要分析留言情緒的影片（comment_sentiment = 0 或 NULL）"""
        self.cursor.execute("""
            SELECT DISTINCT video_uuid, video_id, comment_sentiment
            FROM Youtuber_Financial_Data
            WHERE comment_sentiment = 0 OR comment_sentiment IS NULL
            ORDER BY created_at DESC
        """)
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def update_comment_sentiment_by_uuid(self, video_uuid: str, sentiment: Optional[float]) -> int:
        """
        更新同一影片所有記錄的 comment_sentiment

        Args:
            video_uuid: 影片 UUID
            sentiment: 情緒分數 (-1 到 1)，或 None（留言關閉）

        Returns:
            更新的記錄數
        """
        try:
            self.cursor.execute("""
                UPDATE Youtuber_Financial_Data
                SET comment_sentiment = ?, updated_at = datetime('now')
                WHERE video_uuid = ?
            """, (sentiment, video_uuid))
            self.conn.commit()
            return self.cursor.rowcount
        except Exception as e:
            print(f"❌ 更新 comment_sentiment 失敗: {e}")
            return 0

    # ==================== 統計查詢 ====================

    def get_statistics(self) -> Dict[str, int]:
        """取得資料庫統計資訊"""
        stats = {}

        self.cursor.execute("SELECT COUNT(*) FROM youtubers")
        stats['youtubers'] = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM search_tags")
        stats['tags'] = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM videos")
        stats['videos'] = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
        stats['financial_data'] = self.cursor.fetchone()[0]

        return stats


def main():
    """測試資料庫管理模組"""
    db = DatabaseManager()
    db.connect()
    db.create_tables()

    # 顯示統計
    stats = db.get_statistics()
    print("資料庫統計:")
    print(f"  YouTubers: {stats['youtubers']}")
    print(f"  Tags: {stats['tags']}")
    print(f"  Videos: {stats['videos']}")
    print(f"  Financial Data: {stats['financial_data']}")

    db.close()


if __name__ == '__main__':
    main()
