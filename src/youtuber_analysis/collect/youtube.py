"""YouTube Data API v3 client: video search, metadata and comments."""

from __future__ import annotations

from datetime import datetime, timedelta

import isodate
from googleapiclient.discovery import build


class YouTubeClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY is not set")
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def search_videos(self, query: str, max_results: int = 10, min_age_years: int = 2) -> list[str]:
        """Return IDs of videos matching ``query`` published at least ``min_age_years`` ago.

        Old videos are required so that long-horizon (up to 2-year) stock returns
        can be evaluated.
        """
        cutoff = datetime.now() - timedelta(days=min_age_years * 365)
        response = self.youtube.search().list(
            q=query,
            type="video",
            part="id,snippet",
            maxResults=max_results,
            order="relevance",
            publishedBefore=cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ).execute()
        return [item["id"]["videoId"] for item in response.get("items", [])]

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """Fetch metadata and statistics for up to 50 videos."""
        if not video_ids:
            return []
        response = self.youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(video_ids)
        ).execute()

        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            videos.append({
                "video_id": item["id"],
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "title": snippet["title"],
                "channel_name": snippet["channelTitle"],
                "channel_id": snippet["channelId"],
                "description": snippet["description"],
                "published_at": published.strftime("%Y-%m-%d %H:%M:%S"),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration": str(isodate.parse_duration(item["contentDetails"]["duration"])),
                "thumbnail_default": snippet["thumbnails"]["default"]["url"],
                "thumbnail_medium": snippet["thumbnails"]["medium"]["url"],
                "thumbnail_high": snippet["thumbnails"]["high"]["url"],
            })
        return videos

    def get_video_comments(self, video_id: str, max_comments: int | None = None) -> list[str] | None:
        """Return top-level comments ordered by relevance.

        Returns ``None`` when comments are disabled or the request fails.
        """
        comments: list[str] = []
        page_token = None
        try:
            while True:
                params = {
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": 100,
                    "textFormat": "plainText",
                    "order": "relevance",
                }
                if page_token:
                    params["pageToken"] = page_token
                response = self.youtube.commentThreads().list(**params).execute()

                for item in response.get("items", []):
                    comments.append(item["snippet"]["topLevelComment"]["snippet"]["textDisplay"])
                    if max_comments and len(comments) >= max_comments:
                        return comments

                page_token = response.get("nextPageToken")
                if not page_token:
                    return comments
        except Exception as e:  # noqa: BLE001 - API errors are reported, not raised
            if "commentsDisabled" not in str(e) and "403" not in str(e):
                print(f"  Error fetching comments for {video_id}: {e}")
            return None
