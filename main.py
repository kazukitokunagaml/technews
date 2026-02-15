import logging
import os
import sys

from dotenv import load_dotenv

from qiita_scraper import QiitaScraper
from zenn_scraper import ZennScraper
from send_to_line import LineMessenger

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


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
