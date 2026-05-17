import chromadb
from django.conf import settings
from langdetect import detect
from openai import OpenAI

_openai_client = None
_chroma_client = None


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    return _chroma_client

LANG_MAP = {
    "en": "English", "ar": "Arabic", "fr": "French", "de": "German",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ru": "Russian", "bn": "Bengali",
    "hi": "Hindi", "tr": "Turkish", "nl": "Dutch", "pl": "Polish",
}


def get_collection(bot_id: str):
    """Each bot gets its own isolated ChromaDB collection."""
    return get_chroma_client().get_or_create_collection(
        name=f"bot_{bot_id}",
        metadata={"hnsw:space": "cosine"},
    )


def get_embedding(text: str) -> list:
    """Convert text to embedding vector using OpenAI."""
    response = get_openai_client().embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],  # safe limit
    )
    return response.data[0].embedding


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    Split large text into overlapping chunks.
    Overlap prevents losing context at chunk boundaries.
    """
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
        start = end - overlap
    return chunks


def store_knowledge(text: str, bot_id: str, source_name: str) -> int:
    """
    Chunks text, embeds each chunk, stores in ChromaDB.
    Returns number of chunks stored.
    Called by Celery tasks after scraping/file reading.
    """
    collection = get_collection(bot_id)
    chunks = chunk_text(text)

    # delete old chunks for this source before re-storing
    # (important for rescraping — avoids duplicate data)
    try:
        existing = collection.get(where={"source": source_name})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{source_name}_chunk_{i}"],
            metadatas=[{"source": source_name, "bot_id": bot_id}],
        )

    return len(chunks)


def delete_source_knowledge(bot_id: str, source_name: str):
    """Remove all chunks for a specific source (called when source is deleted)."""
    try:
        collection = get_collection(bot_id)
        existing = collection.get(where={"source": source_name})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass


def search_knowledge(question: str, bot_id: str, top_k: int = 4) -> list[str]:
    """
    Find the most relevant chunks for a question using vector similarity.
    Returns list of matching text chunks.
    """
    collection = get_collection(bot_id)

    # can't search empty collection
    if collection.count() == 0:
        return []

    question_embedding = get_embedding(question)
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=min(top_k, collection.count()),
    )
    return results["documents"][0] if results["documents"] else []


def detect_language(text: str) -> str:
    """Detect language of the user's message."""
    try:
        code = detect(text)
        return LANG_MAP.get(code, "English")
    except Exception:
        return "English"


def get_ai_response(
    question: str,
    bot_id: str,
    business_context: str = "",
    behavior_instructions: str = "",
    chat_history: list = None,
) -> str:
    """
    The main RAG function.
    1. Detect language
    2. Search ChromaDB for relevant chunks
    3. Build system prompt with context + behaviors
    4. Ask OpenAI GPT-4o
    5. Return answer
    """
    # 1 — language detection
    language = detect_language(question)

    # 2 — retrieve relevant knowledge
    relevant_chunks = search_knowledge(question, bot_id)
    context = "\n---\n".join(relevant_chunks) if relevant_chunks else ""

    # 3 — build system prompt
    system_prompt = f"""You are a helpful customer service assistant.

BUSINESS CONTEXT:
{business_context if business_context else "A business assistant."}

{"KNOWLEDGE BASE:" if context else ""}
{context if context else "No specific knowledge base available yet."}

RULES:
- Answer using ONLY the information provided above.
- If the answer is not in the knowledge base, say: "I don't have that information. Please contact our support team."
- Never make up information, prices, policies, or facts.
- Be concise and friendly.
- Respond ONLY in {language}. Match the cultural tone appropriate for {language} speakers.
- If a customer wants a quote, to book a call, or to leave contact details, collect their Name, Email, and Phone one at a time. Once you have all three, respond EXACTLY with: LEAD_CAPTURED::Name::Email::Phone

{"BEHAVIOR INSTRUCTIONS:" if behavior_instructions else ""}
{behavior_instructions if behavior_instructions else ""}
"""

    # 4 — build messages array
    messages = [{"role": "system", "content": system_prompt}]

    if chat_history:
        # include last 6 messages for context (3 exchanges)
        messages.extend(chat_history[-6:])

    messages.append({"role": "user", "content": question})

    # 5 — call OpenAI
    response = get_openai_client().chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=600,
        temperature=0.3,  # lower = more consistent, factual responses
    )

    return response.choices[0].message.content
