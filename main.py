import logging
import os
import sys

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from qiita_scraper import QiitaScraper
from zenn_scraper import ZennScraper
from send_to_line import LineMessenger

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def fetch_article_text(url: str) -> str:
    """Fetch og:description from an article URL to use as article body text."""
    try:
        resp = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "TechDigest/1.0"},
        )
        soup = BeautifulSoup(resp.content, "html.parser")
        meta = soup.find("meta", property="og:description")
        if meta and meta.get("content"):
            return meta["content"]
    except Exception as e:
        logging.warning(f"記事テキスト取得失敗 {url}: {e}")
    return ""


def main():
    load_dotenv()

    # 各プラットフォームから人気記事を取得
    logging.info("=== 記事取得開始 ===")

    # Qiita
    try:
        qiita = QiitaScraper(top_n=5)
        qiita_articles = qiita.run()
    except Exception as e:
        logging.error(f"Qiita取得失敗: {e}")
        qiita_articles = []

    # Zenn
    try:
        zenn = ZennScraper(top_n=5)
        zenn_articles = zenn.run()
    except Exception as e:
        logging.error(f"Zenn取得失敗: {e}")
        zenn_articles = []

    logging.info(f"取得結果: Qiita={len(qiita_articles)}件, Zenn={len(zenn_articles)}件")

    if not any([qiita_articles, zenn_articles]):
        logging.warning("全てのプラットフォームで記事が見つかりませんでした。送信をスキップします。")
        # 0件でも送信を試みる場合は以下の行をコメントアウト
        # return

    # Pinecone へのベクトル保存
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if pinecone_api_key and google_api_key:
        try:
            from vector_store import upsert_articles
            logging.info("=== Pinecone upsert 開始 ===")
            pinecone_articles = []
            for article in qiita_articles + zenn_articles:
                text = fetch_article_text(article["url"])
                pinecone_articles.append({
                    "title": article["title"],
                    "url": article["url"],
                    "text": text or article["title"],
                    "published_at": article.get("published_date", ""),
                })
            upsert_articles(pinecone_articles)
            logging.info("=== Pinecone upsert 完了 ===")
        except Exception as e:
            logging.error(f"Pinecone upsert 失敗: {e}")
    else:
        logging.info("PINECONE_API_KEY または GOOGLE_API_KEY が未設定のため Pinecone upsert をスキップ")

    # LINEに送信
    channel_token = os.getenv("CHANNEL_ACCESS_TOKEN")
    if not channel_token:
        logging.error("CHANNEL_ACCESS_TOKEN が設定されていません")
        sys.exit(1)

    messenger = LineMessenger(channel_access_token=channel_token)
    messenger.send_multi_platform(qiita_articles, zenn_articles)
    logging.info("=== 完了 ===")


if __name__ == "__main__":
    main()
