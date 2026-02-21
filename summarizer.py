import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def summarize(self, title: str, content: str) -> str:
        """記事の内容を要約する"""
        if not content or len(content) < 100:
            logger.info(f"Content too short for summarization: {title}")
            return "（本文が短すぎるため要約をスキップしました）"

        prompt = f"""
以下のテック記事の内容を詳細に要約してください。
読者が内容を把握できるように、重要なポイントを3〜5個の箇条書きでまとめてください。
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
