import asyncio
import json
from sqlalchemy import text
from app.core.database import engine

async def test_cosine():
    print("Testing PL/pgSQL cosine similarity function...")
    async with engine.connect() as conn:
        try:
            # 1. Create the function
            func_sql = """
            CREATE OR REPLACE FUNCTION cosine_similarity_json(a jsonb, b jsonb)
            RETURNS double precision AS $$
            DECLARE
                sum_ab double precision := 0.0;
                sum_a2 double precision := 0.0;
                sum_b2 double precision := 0.0;
                val_a double precision;
                val_b double precision;
                i int;
                len int;
            BEGIN
                len := jsonb_array_length(a);
                IF len IS NULL OR len = 0 OR len != jsonb_array_length(b) THEN
                    RETURN 0.0;
                END IF;
                FOR i IN 0..(len-1) LOOP
                    val_a := (a->i)::double precision;
                    val_b := (b->i)::double precision;
                    sum_ab := sum_ab + (val_a * val_b);
                    sum_a2 := sum_a2 + (val_a * val_a);
                    sum_b2 := sum_b2 + (val_b * val_b);
                END LOOP;
                IF sum_a2 = 0.0 OR sum_b2 = 0.0 THEN
                    RETURN 0.0;
                END IF;
                RETURN sum_ab / (sqrt(sum_a2) * sqrt(sum_b2));
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;
            """
            await conn.execute(text(func_sql))
            await conn.commit()
            print("[SUCCESS] Function cosine_similarity_json created!")

            # 2. Test similarity computation
            v1 = [1.0, 2.0, 3.0]
            v2 = [1.0, 2.0, 3.1]
            q = text("SELECT cosine_similarity_json(:v1, :v2)")
            res = await conn.execute(q, {"v1": json.dumps(v1), "v2": json.dumps(v2)})
            val = res.scalar()
            print(f"[SUCCESS] Cosine similarity between {v1} and {v2} is {val:.6f}")
            assert val > 0.99
        except Exception as e:
            print(f"[FAILED] Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cosine())
