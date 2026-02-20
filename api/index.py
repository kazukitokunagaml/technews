import logging
import os
import sys

# Add project root to sys.path so vector_store can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
import nacl.exceptions
import nacl.signing
from flask import Flask, abort, jsonify, request

from vector_store import query_similar

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "")

# Discord Interaction types
_PING = 1
_APPLICATION_COMMAND = 2

# Discord Interaction response types
_PONG = 1
_CHANNEL_MESSAGE_WITH_SOURCE = 4


def _verify_discord_signature(public_key: str, signature: str, timestamp: str, body: str) -> bool:
    """Discord の Ed25519 署名を検証する"""
    try:
        vk = nacl.signing.VerifyKey(bytes.fromhex(public_key))
        vk.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except (nacl.exceptions.BadSignatureError, Exception):
        return False


def _generate_rag_reply(question: str) -> str:
    """Pinecone で関連記事を検索し、Gemini Flash で回答を生成する"""
    try:
        matches = query_similar(question, top_k=3)

        if not matches:
            return "関連する記事が見つかりませんでした。別のキーワードで試してみてください。"

        context_parts = []
        for match in matches:
            meta = match["metadata"]
            context_parts.append(
                f"タイトル: {meta.get('title', '')}\n"
                f"URL: {meta.get('url', '')}\n"
                f"内容: {meta.get('text', '')}"
            )
        context = "\n\n---\n\n".join(context_parts)

        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = (
            "以下のテック記事を参考に、ユーザーの質問に日本語で簡潔に回答してください。\n\n"
            f"参考記事:\n{context}\n\n"
            f"ユーザーの質問: {question}\n\n"
            "回答は300文字以内にまとめ、関連記事のURLを必ず含めてください。"
        )

        response = model.generate_content(prompt)
        return response.text[:2000]  # Discord message limit

    except Exception as e:
        logger.error(f"RAG処理エラー: {e}")
        return "申し訳ありません。回答の生成中にエラーが発生しました。"


@app.route("/api/index", methods=["POST"])
def interactions():
    """Discord Interactions エンドポイント"""
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")
    body = request.get_data(as_text=True)

    if not _verify_discord_signature(DISCORD_PUBLIC_KEY, signature, timestamp, body):
        logger.warning("Discord署名の検証に失敗しました")
        abort(401)

    data = request.get_json()
    interaction_type = data.get("type")

    # Type 1: PING（Discordの疎通確認）
    if interaction_type == _PING:
        return jsonify({"type": _PONG})

    # Type 2: スラッシュコマンド
    if interaction_type == _APPLICATION_COMMAND:
        command_name = data.get("data", {}).get("name", "")
        if command_name == "ask":
            options = data.get("data", {}).get("options", [])
            question = next((o["value"] for o in options if o["name"] == "question"), "")
            logger.info(f"受信コマンド /ask: {question}")
            reply_text = _generate_rag_reply(question)
            return jsonify({
                "type": _CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {"content": reply_text},
            })

    return jsonify({"type": _PONG})


# Vercel WSGI ハンドラ
handler = app
