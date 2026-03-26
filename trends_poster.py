import datetime
import logging

import google.generativeai as genai
import requests

logger = logging.getLogger(__name__)

JST = datetime.timezone(datetime.timedelta(hours=9))


def detect_period() -> str:
    """昨日(JST)の曜日・月末判定で投稿種別を返す: 'daily' | 'weekly' | 'monthly'"""
    today_jst = datetime.datetime.now(JST).date()
    yesterday = today_jst - datetime.timedelta(days=1)

    # 月末判定（昨日が月の最終日 = 今日と月が異なる）
    if yesterday.month != today_jst.month:
        return "monthly"

    # 日曜判定（weekday: 月=0, 日=6）
    if yesterday.weekday() == 6:
        return "weekly"

    return "daily"


class TrendsPoster:
    def __init__(self, google_api_key: str, webhook_url: str):
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")
        self.webhook_url = webhook_url

    def _collect_articles(self, days_back: int) -> list[dict]:
        """指定日数分の記事を全プラットフォームから収集する"""
        from qiita_scraper import QiitaScraper
        from zenn_scraper import ZennScraper
        from note_scraper import NoteScraper

        # 上位30件に絞るので各プラットフォームは10件ずつ取れれば十分
        platforms = [
            ("Qiita", QiitaScraper(top_n=10, max_pages=3 + days_back // 3, days_back=days_back)),
            ("Zenn",  ZennScraper(top_n=10, max_pages=20 + days_back, days_back=days_back)),
            ("note",  NoteScraper(top_n=10, days_back=days_back)),
        ]

        all_articles = []
        for platform_name, scraper in platforms:
            try:
                articles = scraper.run()
                for a in articles:
                    a["platform"] = platform_name
                all_articles.extend(articles)
                logger.info(f"{platform_name}: {len(articles)}件取得 (trends用, {days_back}日分)")
            except Exception as e:
                logger.warning(f"{platform_name} trends取得エラー: {e}")

        return all_articles

    def generate_trend_summary(self, articles: list[dict], period: str) -> str:
        """記事タイトル一覧から全体的な動向を淡々とまとめる"""
        period_label = {"daily": "昨日", "weekly": "今週", "monthly": "今月"}[period]

        articles_text = "\n".join(
            f"- [{a.get('platform', '')}] {a['title']}"
            for a in articles
        )

        prompt = f"""
以下は{period_label}の技術・個人開発界隈で注目された記事の一覧です。
これらを分析して、{period_label}の全体的な動向・トレンドを淡々と箇条書きでまとめてください。

条件:
- 感情的な表現や煽りは使わない
- 事実ベースで淡々と記述する
- どんな技術・テーマが注目されていたかを3〜5点でまとめる
- 各項目は1〜2文で簡潔に
- 箇条書き（「・」で始める）

記事一覧:
{articles_text}
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"トレンド要約生成エラー: {e}")
            return "（トレンド要約の生成中にエラーが発生しました）"

    def post(self, daily_articles: list[dict]) -> None:
        """動向まとめスレッドをDiscordに投稿する。

        daily_articles: main.pyが当日収集した全記事（日次用）
        週次・月次の場合は内部で再収集する。
        """
        period = detect_period()

        today_jst = datetime.datetime.now(JST).date()
        yesterday = today_jst - datetime.timedelta(days=1)

        if period == "monthly":
            days_back = yesterday.day  # 月初から昨日まで
            articles = self._collect_articles(days_back)
            date_label = yesterday.strftime("%Y年%m月")
            period_label = "月の動向まとめ"
        elif period == "weekly":
            articles = self._collect_articles(7)
            week_start = yesterday - datetime.timedelta(days=6)
            date_label = f"{week_start.strftime('%Y-%m-%d')}〜{yesterday.strftime('%Y-%m-%d')}"
            period_label = "週の動向まとめ"
        else:
            articles = daily_articles
            date_label = yesterday.strftime("%Y-%m-%d")
            period_label = "技術・個人開発界隈の動向"

        thread_name = f"📊 {date_label} {period_label}"
        if len(thread_name) > 100:
            thread_name = thread_name[:97] + "..."

        if not articles:
            logger.warning("動向まとめ: 記事が取得できませんでした。スキップします。")
            return

        # いいね数上位30件に絞ってからGeminiへ渡す（入力トークン削減）
        like_key = lambda a: a.get("like_count") or a.get("liked_count") or a.get("likes_count") or 0
        articles = sorted(articles, key=like_key, reverse=True)[:30]

        logger.info(f"動向まとめ生成中: period={period}, 記事数={len(articles)}")
        summary = self.generate_trend_summary(articles, period)

        content = summary
        if len(content) > 2000:
            content = content[:1997] + "..."

        try:
            resp = requests.post(
                f"{self.webhook_url}?wait=true",
                json={"content": content, "thread_name": thread_name},
                timeout=10,
            )
            resp.raise_for_status()
            thread_id = resp.json().get("channel_id")
            if thread_id:
                logger.info(f"動向まとめスレッド作成: {thread_name} (id={thread_id})")
            else:
                logger.error("thread_id が取得できませんでした: %s", resp.json())
        except Exception as e:
            logger.error(f"動向まとめスレッド投稿エラー: {e}")
