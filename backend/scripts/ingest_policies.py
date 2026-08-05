"""Manually (re)build the Policy RAG vector store from the current
hr_policies table. The app also does this automatically on startup if the
vector store is empty, but re-run this after bulk-editing policy content.

Usage: python -m scripts.ingest_policies
"""

import asyncio

from app.db.session import SessionLocal
from app.services.ai.policy_rag import ingest_all_policies


async def main() -> None:
    async with SessionLocal() as session:
        stats = await ingest_all_policies(session)
    print(f"Ingested {stats['ingested_policies']}/{stats['policies']} policies into {stats['chunks']} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
