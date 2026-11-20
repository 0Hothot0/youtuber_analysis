from youtuber_analysis.analyze.sentiment import comment_sentiment


def test_empty_comments_are_neutral():
    assert comment_sentiment([]) == 0.0


def test_sign_and_line_limit():
    assert comment_sentiment(["This stock is great, I love it!"]) > 0
    assert comment_sentiment(["Terrible, awful company."]) < 0
    # only the first `max_lines` lines are scored
    assert comment_sentiment(["Great!\nAwful."], max_lines=1) > 0
