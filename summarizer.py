import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

    def select_best(self, articles: list[dict]) -> int:
        """記事リストから最も価値のある1記事のインデックスを返す"""
        articles_text = "\n".join(
            f"{i+1}. {a['title']}" for i, a in enumerate(articles)
        )
        prompt = f"""
以下のテック記事リストから、最も技術的に価値があり、読者にとって有益な記事を1つ選んでください。
選定基準:
- 技術的な新規性・革新性
- 実用性の高さ
- 幅広いエンジニアに関連する内容
- トレンドへの関連性

記事リスト:
{articles_text}

最も優れた記事の番号（数字のみ）を返してください。他の文字は一切含めないでください。
"""
        try:
            response = self.model.generate_content(prompt)
            index = int(response.text.strip()) - 1
            if 0 <= index < len(articles):
                return index
        except Exception as e:
            logger.error(f"記事選定エラー: {e}")
        return 0  # フォールバック: 最初の記事

    def summarize(self, title: str, content: str) -> str:
        """記事の内容をアニメの次回予告風ティーザーとして生成する"""
        if not content or len(content) < 100:
            logger.info(f"Content too short for summarization: {title}")
            return "（本文が短すぎるため要約をスキップしました）"

        prompt = f"""
以下のテック記事を3行でまとめてください。

条件:
- 何についての記事かは伝える（読者が興味あるか判断できるように）
- 結論も含めて要点を伝える
- アニメの次回予告のようなテンポとリズムで書く
- 3行、各行30字前後、記号・番号なし

タイトル: {title}
本文:
{content[:4000]}
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini Summarization Error: {e}")
            return "（要約の生成中にエラーが発生しました）"
