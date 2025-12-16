#!/usr/bin/env python3
import time
from db_manager import DatabaseManager

target = 100  # Target analyzed videos
check_interval = 20  # seconds

while True:
    db = DatabaseManager()
    db.connect()

    db.cursor.execute('SELECT COUNT(*) as c FROM videos')
    total = db.cursor.fetchone()['c']

    db.cursor.execute('SELECT COUNT(*) as c FROM Youtuber_Financial_Data')
    analyzed = db.cursor.fetchone()['c']

    db.close()

    remaining = total - analyzed
    progress = (analyzed / total * 100) if total > 0 else 0

    print(f"[{time.strftime('%H:%M:%S')}] {analyzed}/{total} ({progress:.1f}%) | Remaining: {remaining}")

    if analyzed >= target or remaining == 0:
        print(f"\n✓ Target reached: {analyzed} videos analyzed!")
        break

    time.sleep(check_interval)
