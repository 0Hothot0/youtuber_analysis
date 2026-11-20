import pytest

from youtuber_analysis.market.labeling import prediction_class


@pytest.mark.parametrize("sentiment, ret, expected", [
    (0.7, 0.05, 1),     # bullish, rose >= 5%
    (0.7, 0.049, -1),   # bullish, rose < 5%
    (0.7, -0.20, -1),   # bullish, fell
    (0.0, 0.049, 1),    # neutral, flat
    (0.0, -0.049, 1),
    (0.0, 0.05, -1),    # neutral, moved 5%
    (-0.3, -0.05, 1),   # bearish, fell >= 5%
    (-0.3, 0.10, -1),   # bearish, rose
])
def test_prediction_class(sentiment, ret, expected):
    assert prediction_class(sentiment, ret) == expected
