import logging
import os
import sys
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from qiita_scraper import QiitaScraper
from zenn_scraper import ZennScraper
from send_to_discord import DiscordMessenger
from summarizer import Summarizer

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def fetch_article_text(url: str) -> str:
    """記事のURLから本文テキストを抽出する"""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "TechDigest/1.0"})
        soup = BeautifulSoup(resp.content, "html.parser")
        
        content_elem = None
        if "qiita.com" in url:
            content_elem = soup.find("section", class_="it-MdContent")
        elif "zenn.dev" in url:
            content_elem = soup.find("div", class_="znc")
        
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

    logging.info("=== 記事取得開始 ===")
    
    # Qiita & Zenn から記事取得
    qiita_articles = QiitaScraper(top_n=5).run()
    zenn_articles = ZennScraper(top_n=5).run()
    all_articles = qiita_articles + zenn_articles

    summarizer = Summarizer(google_api_key)
    messenger = DiscordMessenger(webhook_url=webhook_url)

    for article in all_articles:
        logging.info(f"処理中: {article['title']}")
        
        text = fetch_article_text(article["url"])
        summary = summarizer.summarize(article["title"], text or article["title"])
        
        # Discord 送信
        messenger.send_article_with_summary(article, summary)
        
        # レート制限対策
        time.sleep(2)

    logging.info("=== 完了 ===")


if __name__ == "__main__":
    main()
