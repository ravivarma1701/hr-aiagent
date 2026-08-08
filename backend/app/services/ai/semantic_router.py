"""Fast, local, free first-pass intent classification via embedding
similarity -- a cheaper and more meaning-aware alternative to both an LLM
call and keyword-regex matching for the common case: a single, self-
contained message with no prior conversation context.

Reuses the same local sentence-transformers model already used for Policy
RAG (embeddings.py) -- no new dependency, no API call, ~10-50ms.

Deliberately NOT a replacement for the LLM-based router in
intent_router.py: this only ever looks at one message in isolation, so it
can't resolve a follow-up like "its a casual leave" answering an earlier
clarifying question -- that requires conversation history, which only the
LLM path is given. See intent_router.classify_intent for how the two are
combined.
"""

from __future__ import annotations

from app.services.ai.embeddings import embed_query, embed_texts

# Deliberately conservative, hand-picked default (not empirically tuned
# against a large eval set): an uncertain match should fall through to the
# LLM/heuristic path rather than confidently misroute.
SIMILARITY_THRESHOLD = 0.55

_INTENT_EXAMPLES: dict[str, list[str]] = {
    "POLICY_QA": [
        "How many sick leaves do I get?",
        "What is the work-from-home policy?",
        "Can I take a half-day leave?",
        "What happens if I log in late?",
        "What is the probation policy?",
        "What is the dress code policy?",
        "Can I work from home on Fridays?",
        "What is the notice period for resignation?",
        "How many casual leaves am I entitled to?",
        "What is the company's leave policy?",
        "Is there a policy for travel reimbursement?",
        "What happens if I miss the clock-in deadline?",
        "What is the policy on sick days?",
        "What's the rule about sick leave here?",
        "How does the sick leave policy work?",
    ],
    "SQL_QUERY": [
        "Which projects are currently ongoing?",
        "Which employees know Python?",
        "Who is assigned to the HR Policy Copilot project?",
        "Show my current project assignments.",
        "Which employees report to my manager?",
        "List all employees in the Engineering department.",
        "Show my leave balance.",
        "Who are the members of the Data Platform team?",
        "Find employees with FastAPI skills.",
        "Show my pending tickets.",
        "What is my current project status?",
        "Which department has the most employees?",
    ],
    "HR_ACTION": [
        "Apply casual leave for tomorrow because of personal work.",
        "Create a high-priority IT ticket for VPN not working.",
        "Approve Employee User's pending leave request.",
        "Assign Employee User to HR Policy Copilot as AI Engineer.",
        "Create an announcement that Friday's townhall is moved to 5 PM.",
        "Raise a ticket for a broken laptop.",
        "Reject this leave request.",
        "Book sick leave for next Monday.",
        "Update the status of ticket 5 to resolved.",
        "Post an announcement about the holiday schedule.",
        "Submit a leave request for next week.",
        "Assign this ticket to the IT team.",
    ],
}

# (intent, example_text, example_embedding) flattened for a simple linear
# scan -- the example set is small (a few dozen rows), so there is no need
# for an index/vector store here.
_example_rows: list[tuple[str, list[float]]] | None = None


def _get_example_rows() -> list[tuple[str, list[float]]]:
    global _example_rows
    if _example_rows is not None:
        return _example_rows

    rows: list[tuple[str, list[float]]] = []
    for intent, examples in _INTENT_EXAMPLES.items():
        for embedding in embed_texts(examples):
            rows.append((intent, embedding))
    _example_rows = rows
    return _example_rows


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    # embed_texts/embed_query normalize their output, so the dot product
    # already equals cosine similarity.
    return sum(x * y for x, y in zip(a, b))


def classify(message: str) -> tuple[str, float] | None:
    """Returns (intent, similarity) if a confident match is found, else
    None. Never raises for a normal string input; the caller should treat
    any exception (e.g. the embedding model failing to load) as "no
    confident match" too."""
    query_embedding = embed_query(message)
    best_intent: str | None = None
    best_score = -1.0
    for intent, example_embedding in _get_example_rows():
        score = _cosine_similarity(query_embedding, example_embedding)
        if score > best_score:
            best_score = score
            best_intent = intent

    if best_intent is not None and best_score >= SIMILARITY_THRESHOLD:
        return best_intent, best_score
    return None
