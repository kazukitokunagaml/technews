import datetime
from unittest.mock import Mock, patch
from qiita_scraper import QiitaScraper

def test_qiita_scraper_returns_articles():
    """Test that Qiita scraper returns list of articles"""
    scraper = QiitaScraper(top_n=5)
    articles = scraper.run()

    assert isinstance(articles, list)
    # May be empty if no articles found, but should be a list
    if articles:
        assert "title" in articles[0]
        assert "url" in articles[0]
        assert articles[0]["url"].startswith("https://qiita.com/")


def test_qiita_scraper_top_n_parameter():
    """Test that top_n parameter limits results correctly"""
    scraper = QiitaScraper(top_n=3, max_pages=1)
    articles = scraper.run()

    assert isinstance(articles, list)
    # Should return at most top_n articles
    assert len(articles) <= 3


def test_qiita_scraper_date_filtering():
    """Test that scraper filters articles by yesterday's date"""
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    scraper = QiitaScraper(top_n=5, max_pages=1)

    # Mock fetch_articles to return mixed dates
    mock_articles = [
        {"title": "Article 1", "url": "https://qiita.com/1", "likes_count": 100, "published_date": yesterday_str},
        {"title": "Article 2", "url": "https://qiita.com/2", "likes_count": 50, "published_date": "2024-01-01"},
        {"title": "Article 3", "url": "https://qiita.com/3", "likes_count": 75, "published_date": yesterday_str},
        {"title": "Article 4", "url": "https://qiita.com/4", "likes_count": 25, "published_date": None},
    ]

    with patch.object(scraper, 'fetch_articles', return_value=mock_articles):
        result = scraper.run()

    # Should only return yesterday's articles
    assert len(result) == 2
    assert result[0]["title"] == "Article 1"  # Higher likes
    assert result[1]["title"] == "Article 3"  # Lower likes


def test_qiita_scraper_sorts_by_likes():
    """Test that scraper sorts articles by likes count"""
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    scraper = QiitaScraper(top_n=3, max_pages=1)

    # Mock fetch_articles to return articles with different like counts
    mock_articles = [
        {"title": "Low", "url": "https://qiita.com/1", "likes_count": 10, "published_date": yesterday_str},
        {"title": "High", "url": "https://qiita.com/2", "likes_count": 100, "published_date": yesterday_str},
        {"title": "Medium", "url": "https://qiita.com/3", "likes_count": 50, "published_date": yesterday_str},
    ]

    with patch.object(scraper, 'fetch_articles', return_value=mock_articles):
        result = scraper.run()

    # Should be sorted by likes (descending)
    assert result[0]["title"] == "High"
    assert result[1]["title"] == "Medium"
    assert result[2]["title"] == "Low"


def test_qiita_scraper_handles_empty_results():
    """Test that scraper handles case with no articles"""
    scraper = QiitaScraper(top_n=5, max_pages=1)

    with patch.object(scraper, 'fetch_articles', return_value=[]):
        result = scraper.run()

    assert isinstance(result, list)
    assert len(result) == 0


def test_qiita_scraper_handles_no_yesterday_articles():
    """Test that scraper handles case with no articles from yesterday"""
    scraper = QiitaScraper(top_n=5, max_pages=1)

    # Mock fetch_articles to return only old articles
    mock_articles = [
        {"title": "Old 1", "url": "https://qiita.com/1", "likes_count": 100, "published_date": "2024-01-01"},
        {"title": "Old 2", "url": "https://qiita.com/2", "likes_count": 50, "published_date": "2024-01-02"},
    ]

    with patch.object(scraper, 'fetch_articles', return_value=mock_articles):
        result = scraper.run()

    assert isinstance(result, list)
    assert len(result) == 0
