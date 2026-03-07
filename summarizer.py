import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def select_best(self, articles: list[dict], prefer_tech: bool = False) -> int:
        """記事リストから最も価値のある1記事のインデックスを返す"""
        articles_text = "\n".join(
            f"{i+1}. {a['title']}" for i, a in enumerate(articles)
        )
        tech_hint = "\n- 技術・プログラミング・AI・開発関連の記事を最優先する" if prefer_tech else ""
        prompt = f"""
以下の記事リストから、最も技術的に価値があり、読者にとって有益な記事を1つ選んでください。
選定基準:
- 技術的な新規性・革新性
- 実用性の高さ
- 幅広いエンジニアに関連する内容
- トレンドへの関連性{tech_hint}

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
        return 0

    def summarize(self, title: str, content: str) -> str:
        """記事の内容を要約する"""
        if not content or len(content) < 100:
            logger.info(f"Content too short for summarization: {title}")
            return "（本文が短すぎるため要約をスキップしました）"

        prompt = f"""
以下のテック記事の内容を詳細に解説してください。
エンジニアが「読む価値があった」と感じられるよう、以下の構成でまとめてください：

1. **一言まとめ**（30字以内）
2. **ポイント解説**（重要な点を3〜5個の箇条書き）
3. **なぜ注目すべきか**（1〜2文）

日本語で出力してください。

タイトル: {title}
本文:
{content[:4000]}
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini Summarization Error: {e}")
            return "（要約の生成中にエラーが発生しました）"
