import os
import logging
import sys
import datetime
from dotenv import load_dotenv

from qiita_scraper import QiitaScraper
from zenn_scraper import ZennScraper
from main import fetch_article_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_scraping():
    load_dotenv()
    
    # テスト用に、昨日と今日の日付で記事取得を試みる
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"=== Testing Qiita Scraper (Target: {today_str} or {yesterday_str}) ===")
    qiita = QiitaScraper(top_n=1)
    
    # 取得できるまで今日、昨日の順に試行
    qiita_articles = []
    for target_date in [today_str, yesterday_str]:
        print(f"Checking Qiita articles for {target_date}...")
        qiita.yesterday_str = target_date
        qiita_articles = qiita.run()
        if qiita_articles:
            break

    if qiita_articles:
        article = qiita_articles[0]
        print(f"Success: Found {len(qiita_articles)} Qiita articles.")
        print(f"Article: {article['title']} ({article['url']})")
        
        text = fetch_article_text(article['url'])
        print(f"Extracted text length: {len(text)} characters.")
        if text:
            preview = text[:100].replace('\n', ' ')
            print(f"Preview (first 100 chars): {preview}...")
    else:
        print("Failed: No Qiita articles found.")

    print("\n=== Testing Zenn Scraper (Target: {today_str} or {yesterday_str}) ===")
    zenn = ZennScraper(top_n=1)

    zenn_articles = []
    for target_date in [today_str, yesterday_str]:
        print(f"Checking Zenn articles for {target_date}...")
        zenn.yesterday_str = target_date
        zenn_articles = zenn.run()
        if zenn_articles:
            break

    if zenn_articles:
        article = zenn_articles[0]
        print(f"Success: Found {len(zenn_articles)} Zenn articles.")
        print(f"Article: {article['title']} ({article['url']})")

        text = fetch_article_text(article['url'])
        print(f"Extracted text length: {len(text)} characters.")
        if text:
            preview = text[:100].replace('\n', ' ')
            print(f"Preview (first 100 chars): {preview}...")
    else:
        print("Failed: No Zenn articles found.")

def test_note_scraper_returns_list():
    """NoteScraper.run() はAPIレスポンスからリストを返す（実HTTPなし）"""
    from unittest.mock import patch, MagicMock
    from note_scraper import NoteScraper

    mock_data = {
        "data": {
            "notes": [
                {"key": "abc123", "name": "テスト技術記事タイトル", "user": {"urlname": "user1"}},
                {"key": "def456", "name": "プログラミング入門記事", "user": {"urlname": "user2"}},
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.Session.get", return_value=mock_resp):
        scraper = NoteScraper(top_n=5)
        articles = scraper.run()

    assert isinstance(articles, list)
    assert len(articles) == 2
    assert articles[0]["title"] == "テスト技術記事タイトル"
    assert articles[0]["url"] == "https://note.com/user1/n/abc123"


def test_select_best_prefer_tech_does_not_crash():
    """select_best(prefer_tech=True) はクラッシュしない"""
    from unittest.mock import MagicMock, patch
    from summarizer import Summarizer

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "1,2"
    mock_model.generate_content.return_value = mock_response

    with patch("google.generativeai.GenerativeModel", return_value=mock_model):
        with patch("google.generativeai.configure"):
            s = Summarizer(api_key="dummy")
            s.model = mock_model
            articles = [{"title": "テスト技術記事"}, {"title": "料理レシピ"}, {"title": "AIニュース"}]
            result = s.select_best(articles, prefer_tech=True, top_n=3)

    assert isinstance(result, list)
    assert all(isinstance(i, int) for i in result)
    assert all(0 <= i < len(articles) for i in result)
    # prefer_tech=True のとき技術優先プロンプトが含まれる
    prompt_used = mock_model.generate_content.call_args[0][0]
    assert "技術・プログラミング" in prompt_used


def test_discord_thread_name_format():
    """post_best_article のスレッド名は '{date} {platform_name} 注目記事' 形式"""
    import datetime
    from unittest.mock import patch, MagicMock
    from send_to_discord import DiscordMessenger

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"channel_id": "123456"}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        messenger = DiscordMessenger(webhook_url="https://discord.com/api/webhooks/test")
        messenger.post_best_article(
            article={"title": "テスト記事", "url": "https://example.com"},
            summary="テスト要約",
            platform_name="Qiita",
            emoji="🗾",
        )

    # 最初のpost呼び出しでスレッド作成
    call_kwargs = mock_post.call_args_list[0][1]
    thread_name = call_kwargs["json"]["thread_name"]
    today = datetime.date.today().strftime("%Y-%m-%d")
    assert thread_name == f"{today} Qiita 注目記事"
    assert "🗾" in call_kwargs["json"]["content"]


if __name__ == "__main__":
    test_scraping()
