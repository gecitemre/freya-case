import os
import logging
from typing import List

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct

logger = logging.getLogger("agent-console")

FAQS = [
    {
        "question": "What is an eSIM?",
        "answer": (
            "An eSIM (embedded SIM) is a digital SIM that allows you to activate a cellular plan "
            "without using a physical SIM card. It's built into your device and can be programmed "
            "with carrier information remotely."
        ),
    },
    {
        "question": "What happens after I pay?",
        "answer": (
            "Your eSIM appears in your profile and in the app. Open the app, tap the eSIM, and follow "
            "the install steps. No QR code needed."
        ),
    },
    {
        "question": "Why sign in?",
        "answer": (
            "So your eSIM is attached to your account and available on all your devices from one place. "
            "We need an account so your eSIM is tied to you."
        ),
    },
    {
        "question": "Is my device compatible with eSIM?",
        "answer": (
            "Most modern smartphones support eSIM, including iPhone XS and later, Google Pixel 3 and later, "
            "Samsung Galaxy S20 and later, and many other devices. Check our compatibility page for a full list."
        ),
    },
    {
        "question": "How do I activate my eSIM?",
        "answer": (
            "After purchase, simply open the Zepliner app and tap to activate your eSIM. It's instant and "
            "automatic - no QR codes or complicated setup required. Your eSIM will be ready to use immediately."
        ),
    },
    {
        "question": "Can I use my eSIM on multiple devices?",
        "answer": (
            "eSIMs are typically tied to one device at a time. However, you can transfer your eSIM to a new "
            "device if needed. Contact our support team for assistance with transfers."
        ),
    },
    {
        "question": "What happens if I reach the plan limit?",
        "answer": (
            "You can easily top up your connectivity through our app or website at any time. We'll also send "
            "you notifications when you're approaching your limit to ensure you stay connected."
        ),
    },
    {
        "question": "Do you offer refunds?",
        "answer": (
            "Yes, we offer a full refund within 30 days of purchase if you haven't used the plan. For unused "
            "portions of activated eSIMs, please contact our support team for pro-rated refund options."
        ),
    },
]


def _client() -> OpenAI:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _qdrant() -> QdrantClient:
    url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    return QdrantClient(url=url)


def _collection() -> str:
    return os.environ.get("QDRANT_COLLECTION", "help_center")


def _embedding_model() -> str:
    return os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def _embed(texts: List[str]) -> List[List[float]]:
    resp = _client().embeddings.create(model=_embedding_model(), input=texts)
    return [item.embedding for item in resp.data]


def init_collection() -> None:
    client = _qdrant()
    name = _collection()

    if not client.collection_exists(name):
        sample_vec = _embed(["sample"])[0]
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=len(sample_vec), distance=Distance.COSINE),
        )

    count = client.count(collection_name=name, exact=True).count
    if count > 0:
        return

    texts = [f"Q: {f['question']}\nA: {f['answer']}" for f in FAQS]
    vectors = _embed(texts)
    points = [
        PointStruct(
            id=i + 1,
            vector=vectors[i],
            payload={"question": FAQS[i]["question"], "answer": FAQS[i]["answer"]},
        )
        for i in range(len(FAQS))
    ]
    client.upsert(collection_name=name, points=points)
    logger.info("RAG: inserted %d FAQ items into Qdrant", len(points))


def retrieve_context(query: str, top_k: int = 3) -> str | None:
    if not query.strip():
        return None

    client = _qdrant()
    name = _collection()
    vector = _embed([query])[0]
    results = client.search(collection_name=name, query_vector=vector, limit=top_k)
    if not results:
        return None

    lines = ["Relevant help-center answers:"]
    for r in results:
        payload = r.payload or {}
        q = payload.get("question", "")
        a = payload.get("answer", "")
        lines.append(f"- Q: {q}\n  A: {a}")
    return "\n".join(lines)
