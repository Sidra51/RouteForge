import asyncio
import json
from sqlalchemy import text, select, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import engine, async_session
from app.services.embedding_service import EmbeddingService
from app.models.cached_prompt import CachedPrompt

async def main():
    p1 = "What is semantic caching?"
    p2 = "What is semantic caching?!"
    
    # 1. Generate embeddings in Python
    v1 = await EmbeddingService.get_embedding(p1, "gemini")
    v2 = await EmbeddingService.get_embedding(p2, "gemini")
    
    print(f"v1 len: {len(v1)}, v2 len: {len(v2)}")
    
    # Calculate cosine similarity in Python
    dot = sum(x * y for x, y in zip(v1, v2))
    sum1 = sum(x * x for x in v1)
    sum2 = sum(x * x for x in v2)
    py_sim = dot / ((sum1 * sum2) ** 0.5)
    print(f"Python Cosine Similarity: {py_sim:.6f}")
    
    # 2. Calculate cosine similarity in Postgres
    async with engine.connect() as conn:
        q = text("SELECT cosine_similarity_json(:v1\\:\\:jsonb, :v2\\:\\:jsonb)")
        res = await conn.execute(q, {"v1": json.dumps(v1), "v2": json.dumps(v2)})
        val = res.scalar()
        print(f"Postgres Cosine Similarity: {val:.6f}")
        
    # 3. Check what is in cached_prompts table and query candidates
    async with async_session() as session:
        query_emb_val = v2  # python list of floats directly
        
        stmt = (
            select(
                CachedPrompt,
                func.cosine_similarity_json(
                    cast(CachedPrompt.embedding, JSONB),
                    cast(query_emb_val, JSONB)
                ).label("similarity")
            )
            .order_by(text("similarity DESC"))
        )
        res = await session.execute(stmt)
        candidates = res.all()
        
        print(f"Candidates found: {len(candidates)}")
        for record, similarity in candidates:
            print(f"Prompt: '{record.prompt}'")
            print(f"  Similarity: {similarity}")
            print(f"  Model: {record.embedding_model}")
            print(f"  Dim: {record.embedding_dimension}")
            print(f"  Created At: {record.created_at}")

if __name__ == "__main__":
    asyncio.run(main())
