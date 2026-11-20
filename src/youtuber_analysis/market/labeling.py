"""Target label: was the YouTuber's call right?"""

from __future__ import annotations


def prediction_class(video_sentiment: float, return_rate: float, threshold: float = 0.05) -> int:
    """Return 1 if the video's sentiment matched the realised return, else -1.

    * bullish (sentiment > 0) and return >= +threshold   -> 1
    * neutral (sentiment = 0) and |return| <  threshold  -> 1
    * bearish (sentiment < 0) and return <= -threshold   -> 1
    * anything else                                      -> -1
    """
    if video_sentiment > 0 and return_rate >= threshold:
        return 1
    if video_sentiment == 0 and -threshold < return_rate < threshold:
        return 1
    if video_sentiment < 0 and return_rate <= -threshold:
        return 1
    return -1
