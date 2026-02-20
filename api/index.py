import logging
import os
import sys

# Add project root to sys.path so vector_store can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from vector_store import query_similar

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""))
line_handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET", ""))


@app.route("/api/index", methods=["POST"])
def callback():
    """LINE Webhook エンドポイント"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        abort(400)

    return "OK"


@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """ユーザーのテキストメッセージを受け取り、RAGで回答を生成して返信する"""
    user_question = event.message.text
    logger.info(f"受信メッセージ: {user_question}")

    try:
        # 1. 質問をベクトル化してPineconeで関連記事を検索
        matches = query_similar(user_question, top_k=3)

        if not matches:
            reply_text = "関連する記事が見つかりませんでした。別のキーワードで試してみてください。"
        else:
            # 2. 取得した記事のテキストをコンテキストとして組み立てる
            context_parts = []
            for match in matches:
                meta = match["metadata"]
                context_parts.append(
                    f"タイトル: {meta.get('title', '')}\n"
                    f"URL: {meta.get('url', '')}\n"
                    f"内容: {meta.get('text', '')}"
                )
            context = "\n\n---\n\n".join(context_parts)

            # 3. Gemini Flash で回答を生成（タイムアウト対策で軽量モデルを使用）
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
            model = genai.GenerativeModel("gemini-2.0-flash")

            prompt = (
                "以下のテック記事を参考に、ユーザーの質問に日本語で簡潔に回答してください。\n\n"
                f"参考記事:\n{context}\n\n"
                f"ユーザーの質問: {user_question}\n\n"
                "回答は300文字以内にまとめ、関連記事のURLを必ず含めてください。"
            )

            response = model.generate_content(prompt)
            reply_text = response.text[:2000]  # LINE メッセージ上限

    except Exception as e:
        logger.error(f"RAG処理エラー: {e}")
        reply_text = "申し訳ありません。回答の生成中にエラーが発生しました。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text),
    )


# Vercel WSGI ハンドラ
handler = app
