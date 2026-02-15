import datetime
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
