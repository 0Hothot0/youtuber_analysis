#!/usr/bin/env python3
"""自動進度報告"""
import sqlite3
import time
from datetime import datetime

last_count = 0
start_time = time.time()

def get_progress():
    conn = sqlite3.connect('youtube_analysis_2years.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(DISTINCT video_id) FROM Youtuber_Financial_Data')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

print("🚀 開始自動監控...")
print()

try:
    while True:
        current = get_progress()
        elapsed = time.time() - start_time
        
        if current != last_count:
            speed = current / (elapsed / 60) if elapsed > 0 else 0
            remaining = 475 - current
            eta_minutes = remaining / speed if speed > 0 else 0
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"進度: {current}/475 ({current*100//475}%) | "
                  f"速度: {speed:.2f} 部/分鐘 | "
                  f"預估剩餘: {format_time(eta_minutes*60)}")
            
            last_count = current
        
        time.sleep(60)  # 每分鐘檢查一次
        
except KeyboardInterrupt:
    print("\n✓ 監控結束")
