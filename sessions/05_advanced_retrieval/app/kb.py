"""The Qdrant knowledge base of the Session 05 lab: one collection, two named vectors (dense + BM25), hybrid search.

Start the server first: `docker compose up -d` (in the session folder). Used by app/ingest.py, the notebook
02_qdrant_documents_agent.ipynb and app/kb_mcp_server.py.
"""
import os
import re
import uuid
from functools import cache

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models

COLLECTION = "gia_dien"
DENSE, SPARSE = "dense", "bm25"          # names of the two vectors of every point
EMBED_MODEL, EMBED_DIM = "text-embedding-3-small", 1536
# Server-side BM25 (Qdrant tokenizes the text, no model download). Vietnamese is not one of Qdrant's stopword /
# stemmer languages, so both are switched off explicitly: with ascii_folding the default English stopwords would
# delete "thẻ" → "the" and "tơ" → "to". ascii_folding lets "gia dien" (no diacritics) match "giá điện".
# The SAME options must be used at index time and at query time.
BM25_OPTIONS = {"ascii_folding": True, "stopwords": {"custom": []}, "stemmer": {"type": "none"}}
PREFETCH_LIMIT = 20  # candidates from each retriever before fusion
TOP_K = 8            # passages a search tool returns: enough for an old and a new version of the same table


QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")  # 127.0.0.1, not localhost: the port is bound on IPv4


@cache
def client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, timeout=30)


def check_server() -> None:
    """Fail fast with the start command when the Qdrant server does not answer."""
    try:
        client().get_collections()
    except Exception as exc:
        raise RuntimeError(f"No Qdrant server at {QDRANT_URL}. Start Docker, then in the session folder run "
                           "`docker compose up -d` and check `docker compose ps` (README, step 5).") from exc


@cache
def embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBED_MODEL)


def bm25(text: str) -> models.Document:
    """Text for the server-side BM25 model; Qdrant turns it into a sparse vector."""
    return models.Document(text=text, model="qdrant/bm25", options=BM25_OPTIONS)


# ── Collection ───────────────────────────────────────────────────────────────
def create_collection(name: str = COLLECTION) -> None:
    """(Re)create the collection with a dense and a sparse vector, then the payload indexes used by filters.
    Indexes are created before the upsert so Qdrant builds them while points arrive."""
    qc = client()
    if qc.collection_exists(name):
        qc.delete_collection(name)
    qc.create_collection(
        name,
        vectors_config={DENSE: models.VectorParams(size=EMBED_DIM, distance=models.Distance.COSINE)},
        sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},  # IDF: BM25 needs it
    )
    for field, schema in [("doc_id", models.PayloadSchemaType.KEYWORD),
                          ("access_group", models.PayloadSchemaType.KEYWORD),
                          ("effective_date", models.PayloadSchemaType.DATETIME),
                          ("page", models.PayloadSchemaType.INTEGER)]:
        qc.create_payload_index(name, field, field_schema=schema)


def upsert_chunks(chunks: list[dict], name: str = COLLECTION) -> None:
    """One point per chunk: both vectors + the chunk dict as payload. The id is a UUID derived from the doc id and
    the chunk's position in the corpus, so running the ingest again overwrites the same points instead of adding copies."""
    dense = embeddings().embed_documents([c["text"] for c in chunks])
    points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{c['doc_id']}#{i}")),
                                 vector={DENSE: vector, SPARSE: bm25(c["text"])}, payload=c)
              for i, (c, vector) in enumerate(zip(chunks, dense))]
    client().upsert(name, points, wait=True)


# ── Search ───────────────────────────────────────────────────────────────────
def access_filter(access_groups: list[str], effective_after: str | None = None) -> models.Filter:
    """Only chunks the user may read (and, optionally, documents that took effect on or after a date)."""
    must = [models.FieldCondition(key="access_group", match=models.MatchAny(any=access_groups))]
    if effective_after:
        must.append(models.FieldCondition(key="effective_date", range=models.DatetimeRange(gte=effective_after)))
    return models.Filter(must=must)


def dense_search(query: str, k: int = 5, query_filter: models.Filter | None = None):
    return client().query_points(COLLECTION, query=embeddings().embed_query(query), using=DENSE,
                                 query_filter=query_filter, limit=k).points


def bm25_search(query: str, k: int = 5, query_filter: models.Filter | None = None):
    return client().query_points(COLLECTION, query=bm25(query), using=SPARSE, query_filter=query_filter,
                                 limit=k).points


def hybrid_search(query: str, access_groups: list[str], k: int = TOP_K, effective_after: str | None = None):
    """Dense and BM25 candidates (prefetch), fused by rank with RRF, in one Query API call.
    The top-level filter also applies inside both prefetches. RRF scores are ranks, not similarities."""
    return client().query_points(
        COLLECTION,
        prefetch=[models.Prefetch(query=embeddings().embed_query(query), using=DENSE, limit=PREFETCH_LIMIT),
                  models.Prefetch(query=bm25(query), using=SPARSE, limit=PREFETCH_LIMIT)],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        query_filter=access_filter(access_groups, effective_after),
        limit=k,
    ).points


def search_text(query: str, access_groups: list[str], effective_after: str | None = None) -> str:
    """What both retrieval tools return (notebook 02 and the MCP server): formatted hits, or a message the model
    can act on when an argument is invalid (input errors go back to the model as text, not as exceptions)."""
    if effective_after and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", effective_after):
        return "effective_after must be a date YYYY-MM-DD, e.g. 2025-01-01."
    return format_hits(hybrid_search(query, access_groups, effective_after=effective_after))


def format_hits(points) -> str:
    """Chunks with a citation header the agent can copy: [title | trang N | hiệu lực YYYY-MM-DD]."""
    if not points:
        return "No matching passages."
    return "\n\n".join(f"[{p.payload['title']} | trang {p.payload['page']} | hiệu lực {p.payload['effective_date'][:10]}]\n"
                       + p.payload["text"].split("\n", 1)[1]  # the first line repeats the title
                       for p in points)
