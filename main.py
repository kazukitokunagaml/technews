import logging
import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from qiita_scraper import QiitaScraper
from zenn_scraper import ZennScraper
from note_scraper import NoteScraper
from send_to_discord import DiscordMessenger
from summarizer import Summarizer
from trends_poster import TrendsPoster

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def fetch_article_text(url: str) -> str:
    """記事のURLから本文テキストを抽出する"""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "TechDigest/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        
        content_elem = None
        if "qiita.com" in url:
            content_elem = soup.find("section", class_="it-MdContent")
        elif "zenn.dev" in url:
            content_elem = soup.find("div", class_="znc")
        elif "note.com" in url:
            content_elem = soup.find("div", class_="note-common-styles__textnote-body")
        if not content_elem:
            content_elem = soup.find("article") or soup.find("main")
            
        if content_elem:
            for s in content_elem(["script", "style"]):
                s.decompose()
            return content_elem.get_text(strip=True, separator="\n")
            
        meta = soup.find("meta", property="og:description")
        return meta["content"] if meta else ""
    except Exception as e:
        logging.warning(f"記事テキスト取得失敗 {url}: {e}")
    return ""


def main():
    load_dotenv()

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not webhook_url or not google_api_key:
        logging.error("DISCORD_WEBHOOK_URL または GOOGLE_API_KEY が設定されていません")
        sys.exit(1)

    PLATFORMS = [
        ("Qiita",  "🗾", QiitaScraper(top_n=5),  True),
        ("Zenn",   "📚", ZennScraper(top_n=5),   True),
        ("note",   "📝", NoteScraper(top_n=5),   True),
    ]

    summarizer = Summarizer(google_api_key)
    messenger = DiscordMessenger(webhook_url=webhook_url)
    trends_poster = TrendsPoster(google_api_key=google_api_key, webhook_url=webhook_url)

    logging.info("=== 記事取得開始 ===")

    # 各プラットフォームのいいね数1位記事を収集（select_best不要）
    best_articles = []  # [(article, platform_name, emoji)]
    all_collected_articles = []

    for platform_name, emoji, scraper, _ in PLATFORMS:
        logging.info(f"--- {platform_name} スクレイピング ---")
        articles = scraper.run()

        if not articles:
            logging.warning(f"{platform_name}: 記事が取得できませんでした。スキップします。")
            continue

        # 動向まとめ用に全記事を蓄積（platformフィールドを付与）
        for a in articles:
            a["platform"] = platform_name
        all_collected_articles.extend(articles)

        # いいね数でソート済みなので先頭が最良
        best_articles.append((articles[0], platform_name, emoji))
        logging.info(f"{platform_name} 選定: {articles[0]['title']}")

    # 全プラットフォームをまとめて1回のGemini呼び出しで要約
    logging.info("--- まとめて要約生成 ---")
    items = [
        {"title": a["title"], "content": fetch_article_text(a["url"])}
        for a, _, _ in best_articles
    ]
    summaries = summarizer.batch_summarize(items)

    for (article, platform_name, emoji), summary in zip(best_articles, summaries):
        messenger.post_best_article(article, summary, platform_name, emoji)

    logging.info("--- 動向まとめ投稿開始 ---")
    trends_poster.post(all_collected_articles)

    logging.info("=== 完了 ===")


if __name__ == "__main__":
    main()
