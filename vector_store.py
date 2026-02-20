import hashlib
import logging
import os

import google.generativeai as genai
from pinecone import Pinecone

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "models/text-embedding-004"


def _get_index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(os.environ["PINECONE_INDEX_NAME"])


def _embed_text(text: str) -> list:
    """Embed text using Gemini text-embedding-004 (768 dimensions)."""
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    result = genai.embed_content(
        model=_EMBEDDING_MODEL,
        content=text,
    )
    return result["embedding"]


def _url_to_id(url: str) -> str:
    """Convert URL to a stable, deduplicated ID using MD5 hash."""
    return hashlib.md5(url.encode()).hexdigest()


def upsert_articles(articles: list) -> None:
    """Vectorize and upsert articles to Pinecone.

    Each article dict must have:
        title (str), url (str), text (str), published_at (str)
    """
    if not articles:
        return

    index = _get_index()
    vectors = []

    for article in articles:
        text = article.get("text") or article.get("title", "")
        if not text:
            continue

        try:
            embedding = _embed_text(text)
            vec_id = _url_to_id(article["url"])
            vectors.append({
                "id": vec_id,
                "values": embedding,
                "metadata": {
                    "title": article.get("title", ""),
                    "url": article["url"],
                    "text": text,
                    "published_at": article.get("published_at", ""),
                },
            })
            logger.info(f"Embedded: {article.get('title', '')[:60]}")
        except Exception as e:
            logger.error(f"Embedding failed for {article.get('url', '')}: {e}")
            continue

    if vectors:
        index.upsert(vectors=vectors)
        logger.info(f"Upserted {len(vectors)} articles to Pinecone")


def query_similar(question: str, top_k: int = 3) -> list:
    """Query Pinecone for articles similar to the question.

    Returns a list of dicts: [{id, score, metadata: {title, url, text, published_at}}]
    """
    index = _get_index()
    q_vector = _embed_text(question)
    result = index.query(vector=q_vector, top_k=top_k, include_metadata=True)

    matches = []
    for match in result.matches:
        matches.append({
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata or {},
        })
    return matches
