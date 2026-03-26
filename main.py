import logging
import os
import sys
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from qiita_scraper import QiitaScraper
from zenn_scraper import ZennScraper
from note_scraper import NoteScraper
from hackernews_scraper import HackerNewsScraper
from devto_scraper import DevToScraper
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
        ("Qiita",        "🗾", QiitaScraper(top_n=5, min_likes=1)),
        ("Zenn",         "📚", ZennScraper(top_n=5, min_likes=1)),
        ("note",         "📝", NoteScraper(top_n=5, min_likes=1)),
        ("Hacker News",  "🔶", HackerNewsScraper(top_n=5, min_score=10)),
        ("dev.to",       "👩‍💻", DevToScraper(top_n=5, min_reactions=5)),
    ]

    summarizer = Summarizer(google_api_key)
    messenger = DiscordMessenger(webhook_url=webhook_url)
    trends_poster = TrendsPoster(google_api_key=google_api_key, webhook_url=webhook_url)

    logging.info("=== 記事取得開始（並列） ===")

    # スクレイピングを並列実行
    def scrape(platform_name, emoji, scraper):
        articles = scraper.run()
        return platform_name, emoji, articles

    platform_results = {}  # platform_name -> (emoji, articles)
    with ThreadPoolExecutor(max_workers=len(PLATFORMS)) as executor:
        futures = {
            executor.submit(scrape, name, emoji, scraper): name
            for name, emoji, scraper in PLATFORMS
        }
        for future in as_completed(futures):
            try:
                platform_name, emoji, articles = future.result()
                platform_results[platform_name] = (emoji, articles)
            except Exception as e:
                name = futures[future]
                logging.error(f"{name} スクレイピング例外: {e}")
                platform_results[name] = (None, [])

    # プラットフォーム順を維持しつつ結果を整理
    best_articles = []   # [(article, platform_name, emoji)]
    all_collected_articles = []

    for platform_name, emoji, _ in PLATFORMS:
        emoji, articles = platform_results.get(platform_name, (emoji, []))
        if not articles:
            logging.warning(f"{platform_name}: 記事が取得できませんでした。スキップします。")
            continue

        for a in articles:
            a["platform"] = platform_name
        all_collected_articles.extend(articles)

        best_articles.append((articles[0], platform_name, emoji))
        logging.info(f"{platform_name} 選定: {articles[0]['title']}")

    if not best_articles:
        logging.error("全プラットフォームで記事が取得できませんでした")
        messenger.post_error_notification(
            "⚠️ 全プラットフォームで記事が取得できませんでした。スクレイパーの確認が必要です。"
        )
        sys.exit(1)

    # 本文取得を並列化
    logging.info("--- 本文取得（並列） ---")
    with ThreadPoolExecutor(max_workers=len(best_articles)) as executor:
        text_futures = {
            executor.submit(fetch_article_text, a["url"]): i
            for i, (a, _, _) in enumerate(best_articles)
        }
        texts = [""] * len(best_articles)
        for future in as_completed(text_futures):
            i = text_futures[future]
            try:
                texts[i] = future.result()
            except Exception as e:
                logging.warning(f"本文取得失敗 (index={i}): {e}")

    # まとめて1回のGemini呼び出しで要約
    logging.info("--- まとめて要約生成 ---")
    items = [
        {"title": a["title"], "content": text or a["title"]}
        for (a, _, _), text in zip(best_articles, texts)
    ]
    summaries = summarizer.batch_summarize(items)

    for (article, platform_name, emoji), summary in zip(best_articles, summaries):
        messenger.post_best_article(article, summary, platform_name, emoji)

    logging.info("--- 動向まとめ投稿開始 ---")
    trends_poster.post(all_collected_articles)

    logging.info("=== 完了 ===")


if __name__ == "__main__":
    main()
