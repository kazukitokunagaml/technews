import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)

_SEPARATOR = "---"


class Summarizer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

    def batch_summarize(self, items: list[dict]) -> list[str]:
        """複数記事をまとめて1回のGemini呼び出しで要約する。

        items: [{"title": str, "content": str}, ...]
        戻り値: 各記事の要約テキストリスト（itemsと同じ順序）
        """
        if not items:
            return []

        blocks = []
        for i, item in enumerate(items):
            content = item.get("content", "")
            body = content[:1500] if content else item["title"]
            blocks.append(f"[記事{i+1}]\nタイトル: {item['title']}\n本文:\n{body}")

        articles_text = f"\n{_SEPARATOR}\n".join(blocks)

        prompt = f"""
以下の{len(items)}本の記事をそれぞれ3行でまとめてください。

条件:
- 何を作ったか・何を学んだか・どんな方法論を提唱しているかが伝わるようにする
- 個人開発者やプロダクト開発に携わる人として得られる学びや行動につながる要点を含める
- アニメの次回予告のようなテンポとリズムで書く
- 3行、各行30字前後、記号・番号なし

出力形式: 記事ごとの要約を「{_SEPARATOR}」だけの行で区切って並べる。他の文字は含めない。

{articles_text}
"""
        try:
            response = self.model.generate_content(prompt)
            parts = response.text.strip().split(f"\n{_SEPARATOR}\n")
            results = [p.strip() for p in parts]
            # 数が合わない場合は対応する要約を返す（フォールバック）
            while len(results) < len(items):
                results.append("（要約取得失敗）")
            return results[: len(items)]
        except Exception as e:
            logger.error(f"Gemini batch summarize error: {e}")
            return ["（要約の生成中にエラーが発生しました）"] * len(items)
