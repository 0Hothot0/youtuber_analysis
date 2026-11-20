"""Gemini (Vertex AI) analysis of YouTube videos.

Gemini watches each video and returns one record per PRIMARY stock discussed,
with 17 structured indicators (sentiment, financial ratio, celebrity, ...).
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid

from google import genai
from google.genai.types import GenerateContentConfig, Part

from .. import db as dbm

ANALYSIS_PROMPT = """
Analyze this YouTube financial video and identify ALL PRIMARY stocks discussed.

PRIMARY stocks are those that meet at least one condition:
- The host spends significant time discussing it
- The video includes analysis, data, charts, earnings, or price commentary about it
- The stock is part of the main topic or title of the video

IGNORE casually mentioned stocks (brief mentions, comparisons, examples without analysis).

Return a JSON array. For EACH primary stock, provide one complete entry.
If NO primary stocks are found, return: []

Return ONLY valid JSON, no other text:

[
  {
    "stock_ticker": "SYMBOL",
    "text_type": 0,
    "video_sentiment": 0.0,
    "financial_ratio": 0.0,
    "celebrity": 0,
    "relevancy": 0.0,
    "long_term_competitiveness": 0,
    "short_term_focus": 0,
    "ceo_leadership_style": 0,
    "earnings_expectation_gap": 0.0,
    "stock_price_growth_trend": 0.0,
    "market_demand": 0.0,
    "market_capitalization": 0,
    "target_price": 0,
    "financial_health": 0.0,
    "valuation": 0.0,
    "policy_impact": 0.0
  }
]

Field definitions:
1. stock_ticker (TEXT): Stock symbol (e.g., "AAPL", "TSLA", "NVDA"). Required.
2. text_type (INTEGER): 1=functional (analysis/data/facts), 0=social-bond (opinion/views)
3. video_sentiment (REAL): -1 (very negative) to 1 (very positive), 0=neutral/no mention
4. financial_ratio (REAL): 0 to 1, proportion of financial elements (charts, numbers, terms)
5. celebrity (INTEGER): 1=mentions famous investors/CEOs, 0=none
6. relevancy (REAL): 0 to 1, relevance between video content and core stock message
7. long_term_competitiveness (INTEGER): 1=discusses long-term growth/industry trends, 0=no
8. short_term_focus (INTEGER): 1=focuses on recent news/short-term catalysts, 0=no
9. ceo_leadership_style (INTEGER): 1=mentions CEO management style/vision, 0=no
10. earnings_expectation_gap (REAL): -1 to 1, -1=below expectations, 0=neutral, 1=above
11. stock_price_growth_trend (REAL): -1 to 1, -1=declining, 0=neutral, 1=growing
12. market_demand (REAL): -1 to 1, -1=weak demand, 0=neutral, 1=strong demand
13. market_capitalization (INTEGER): 1=mentions market cap, 0=no
14. target_price (INTEGER): 1=mentions analyst price target, 0=no
15. financial_health (REAL): -1 to 1, -1=weak, 0=neutral, 1=strong
16. valuation (REAL): -1 to 1, -1=overvalued, 0=fairly priced, 1=undervalued
17. policy_impact (REAL): -1 to 1, -1=negative policy impact, 0=neutral, 1=positive

CRITICAL: If a metric is not mentioned in the video, use 0 or 0.0. Do NOT infer or assume values.
"""

INDICATOR_DEFAULTS = {
    "text_type": 0, "video_sentiment": 0.0, "financial_ratio": 0.0, "celebrity": 0,
    "relevancy": 0.0, "long_term_competitiveness": 0, "short_term_focus": 0,
    "ceo_leadership_style": 0, "earnings_expectation_gap": 0.0,
    "stock_price_growth_trend": 0.0, "market_demand": 0.0, "market_capitalization": 0,
    "target_price": 0, "financial_health": 0.0, "valuation": 0.0, "policy_impact": 0.0,
}


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    for prefix in ("```json", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class GeminiVideoAnalyzer:
    def __init__(self, project_id: str, location: str = "us-central1",
                 model: str = "gemini-2.0-flash-exp"):
        self.model = model
        self.client = genai.Client(vertexai=True, project=project_id, location=location)

    def analyze_video(self, youtube_url: str, max_retries: int = 3) -> list[dict]:
        """Return one dict per primary stock (empty list on failure / no stocks)."""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[Part.from_uri(file_uri=youtube_url, mime_type="video/*"),
                              ANALYSIS_PROMPT],
                    config=GenerateContentConfig(temperature=0.2, max_output_tokens=2048),
                )
                result = json.loads(_strip_code_fence(response.text))
                if isinstance(result, dict):
                    result = [result]
                if not isinstance(result, list):
                    raise ValueError(f"expected a JSON array, got {type(result).__name__}")
                return result
            except Exception as e:  # noqa: BLE001 - retried with backoff
                print(f"  attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return []


def save_analyses(conn: sqlite3.Connection, video_id: str, analyses: list[dict]) -> int:
    """Store the analyses of one video; all its stocks share one ``video_uuid``."""
    video = conn.execute(
        "SELECT like_count, comment_count, view_count, published_at, channel_name "
        "FROM videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    if video is None or not analyses:
        return 0

    video_uuid = str(uuid.uuid4())
    raw_json = json.dumps(analyses, ensure_ascii=False)
    saved = 0
    for analysis in analyses:
        ticker = analysis.get("stock_ticker")
        if not ticker:
            continue
        row = {k: analysis.get(k, default) for k, default in INDICATOR_DEFAULTS.items()}
        row.update(
            video_uuid=video_uuid,
            video_id=video_id,
            stock_ticker=ticker,
            like_number=video["like_count"],
            comment_number=video["comment_count"],
            view_number=video["view_count"],
            published_time=video["published_at"],
            comment_sentiment=0,  # filled in later by the comment-sentiment step
            raw_json=raw_json,
            youtuber=video["channel_name"],
        )
        saved += dbm.insert_analysis(conn, row)
    conn.commit()
    return saved


def pending_videos(conn: sqlite3.Connection, limit: int,
                   channel_name: str | None = None) -> list[sqlite3.Row]:
    """Videos in the ``videos`` table that have no analysis yet."""
    sql = """
        SELECT v.video_id, v.url, v.title
        FROM videos v
        LEFT JOIN Youtuber_Financial_Data f ON v.video_id = f.video_id
        WHERE f.id IS NULL {extra}
        ORDER BY v.created_at DESC
        LIMIT ?
    """
    if channel_name:
        return conn.execute(sql.format(extra="AND v.channel_name = ?"),
                            (channel_name, limit)).fetchall()
    return conn.execute(sql.format(extra=""), (limit,)).fetchall()
