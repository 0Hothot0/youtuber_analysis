#!/usr/bin/env python3
"""
Gemini 分析結果匯入器
讀取 Gemini 回傳的 JSON 並匯入至 Youtuber_Financial_Data 資料表
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from .db_manager import DatabaseManager


def load_json_file(file_path: str) -> Dict[str, Any]:
    """載入 JSON 檔案"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_financial_data(data: Dict[str, Any]) -> bool:
    """
    驗證財務資料格式

    必要欄位：
    - video_id: 影片 ID
    """
    required_fields = ['video_id']

    for field in required_fields:
        if field not in data:
            print(f"⚠️ 缺少必要欄位: {field}")
            return False

    return True


def normalize_financial_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    標準化 Gemini 回傳的資料格式

    將 Gemini 的欄位名稱對應到資料庫欄位
    """
    normalized = {
        'video_id': raw_data.get('video_id'),
        'stock_ticker': raw_data.get('stock_ticker'),
        'like_number': raw_data.get('like_number'),
        'comment_number': raw_data.get('comment_number'),
        'view_number': raw_data.get('view_number'),
        'text_type': raw_data.get('text_type'),
        'video_sentiment': raw_data.get('video_sentiment'),
        'comment_sentiment': raw_data.get('comment_sentiment'),
        'financial_ratio': raw_data.get('financial_ratio'),
        'celebrity': raw_data.get('celebrity'),
        'relevancy': raw_data.get('relevancy'),
        'published_time': raw_data.get('published_time'),
        'long_term_competitiveness': raw_data.get('long_term_competitiveness'),
        'short_term_focus': raw_data.get('short_term_focus'),
        'ceo_leadership_style': raw_data.get('ceo_leadership_style'),
        'earnings_expectation_gap': raw_data.get('earnings_expectation_gap'),
        'stock_price_growth_trend': raw_data.get('stock_price_growth_trend'),
        'market_demand': raw_data.get('market_demand'),
        'market_capitalization': raw_data.get('market_capitalization'),
        'target_price': raw_data.get('target_price'),
        'financial_health': raw_data.get('financial_health'),
        'valuation': raw_data.get('valuation'),
        'policy_impact': raw_data.get('policy_impact'),
        'raw_json': json.dumps(raw_data, ensure_ascii=False)  # 保存原始 JSON
    }

    return normalized


def import_single_analysis(data: Dict[str, Any], db: DatabaseManager) -> bool:
    """匯入單筆分析結果"""
    if not validate_financial_data(data):
        return False

    # 檢查影片是否存在於資料庫
    video = db.get_video_by_video_id(data['video_id'])
    if not video:
        print(f"⚠️ 警告：影片 {data['video_id']} 不存在於 videos 資料表")
        # 仍然繼續匯入，但提醒用戶

    # 標準化資料
    normalized_data = normalize_financial_data(data)

    # 匯入至資料庫
    result_id = db.insert_financial_data(normalized_data)

    if result_id:
        print(f"✓ 成功匯入分析結果 (ID: {result_id}) for video: {data['video_id']}")
        return True
    else:
        print(f"❌ 匯入失敗 for video: {data['video_id']}")
        return False


def import_batch_analysis(data_list: List[Dict[str, Any]], db: DatabaseManager):
    """批次匯入分析結果"""
    success_count = 0
    fail_count = 0

    for data in data_list:
        if import_single_analysis(data, db):
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"匯入統計:")
    print(f"  成功: {success_count}")
    print(f"  失敗: {fail_count}")
    print(f"{'='*60}")


def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("\n使用方式:")
        print(f"  python {sys.argv[0]} <json_file>")
        print(f"\n範例:")
        print(f"  python {sys.argv[0]} gemini_analysis.json")
        print(f"  python {sys.argv[0]} gemini_batch.json\n")
        sys.exit(1)

    json_file = sys.argv[1]

    print("\n" + "="*60)
    print("Gemini 分析結果匯入工具")
    print("="*60 + "\n")

    try:
        # 載入 JSON 檔案
        print(f"載入 JSON 檔案: {json_file}")
        data = load_json_file(json_file)
        print("✓ JSON 檔案載入成功\n")

        # 連接資料庫
        db = DatabaseManager()
        db.connect()

        # 判斷是單筆還是批次資料
        if isinstance(data, list):
            print(f"偵測到批次資料 ({len(data)} 筆)\n")
            import_batch_analysis(data, db)
        elif isinstance(data, dict):
            print("偵測到單筆資料\n")
            import_single_analysis(data, db)
        else:
            print("❌ 錯誤：JSON 格式不正確")
            print("期望格式: 單個物件 {} 或物件陣列 [{}, {}]")
            sys.exit(1)

        # 顯示統計
        print("\n資料庫統計:")
        stats = db.get_statistics()
        print(f"  Financial Data: {stats['financial_data']}")

        db.close()
        print("\n✓ 匯入完成！\n")

    except FileNotFoundError:
        print(f"❌ 錯誤：找不到檔案 {json_file}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析錯誤: {str(e)}")
    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
