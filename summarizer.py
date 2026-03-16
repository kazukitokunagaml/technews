import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

    def select_best(
        self, articles: list[dict], prefer_tech: bool = False, top_n: int = 3
    ) -> list[int]:
        """記事リストから価値のある上位top_n記事のインデックスリストを返す"""
        if not articles:
            return [0]
        actual_n = min(top_n, len(articles))
        articles_text = "\n".join(
            f"{i+1}. {a['title']}" for i, a in enumerate(articles)
        )
        prompt = f"""
あなたは個人開発に関心を持つエンジニア向けのキュレーターです。
以下の記事リストから、個人開発者にとって最も価値のある記事を上位{actual_n}つ選んでください。

選定基準（優先度順）:
- 個人がサービス・アプリ・ツールを作った体験・知見を共有している
- 個人開発の効率化・自動化・スピードアップに役立つ技術やツールの紹介
- 個人開発のマネタイズ・リリース・グロースに関する実践的な事例
- 個人開発者が直面する課題の解決策や tips
- 個人でも使えるAI・クラウド・OSSの活用事例
- プロダクト開発の方法論・思想・プロセスを実践者が発信しているもの（スタートアップ・個人・小規模チームの事例が特に望ましい）

除外すべき記事:
- 大企業の組織論・採用情報・IR関連
- 学術的すぎて個人開発に応用しにくい内容
- 技術的な内容を含まない純粋なビジネス・マーケティング記事

記事リスト:
{articles_text}

上位{actual_n}記事の番号をカンマ区切り（例: 2,5,1）で返してください。他の文字は一切含めないでください。
"""
        try:
            response = self.model.generate_content(prompt)
            indices = [int(x.strip()) - 1 for x in response.text.strip().split(",")]
            valid = [i for i in indices if 0 <= i < len(articles)]
            if valid:
                return valid[:actual_n]
        except Exception as e:
            logger.error(f"記事選定エラー: {e}")
        return list(range(actual_n))

    def summarize(self, title: str, content: str) -> str:
        """記事の内容をアニメの次回予告風ティーザーとして生成する"""
        if not content or len(content) < 100:
            logger.info(f"Content too short for summarization: {title}")
            return "（本文が短すぎるため要約をスキップしました）"

        prompt = f"""
以下の記事を3行でまとめてください。

条件:
- 何を作ったか・何を学んだか・どんな方法論を提唱しているかが伝わるようにする（読者が自分に関係あるか判断できるように）
- 個人開発者やプロダクト開発に携わる人として得られる学びや行動につながる要点を含める
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
