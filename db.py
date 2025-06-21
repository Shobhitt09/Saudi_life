import hashlib
import uuid
import asyncio
from typing import List
from fastapi import FastAPI, Request
from bs4 import BeautifulSoup
from redis.commands.search.query import Query
import aiohttp
import redis
import numpy as np
from sentence_transformers import SentenceTransformer
import uvicorn
from src.common.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

app = FastAPI()

class VectorDatabase:
    def __init__(self):
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, ssl=False)
        self.hash_cache = {}
        self.create_redis_index()

    def create_redis_index(self):
        try:
            self.redis_client.ft("content_index").info()
        except:
            self.redis_client.ft("content_index").create_index([
                redis.commands.search.field.TextField("url"),
                redis.commands.search.field.TextField("chunk"),
                redis.commands.search.field.VectorField(
                    "embedding",
                    "FLAT", {
                        "TYPE": "FLOAT32",
                        "DIM": 384,
                        "DISTANCE_METRIC": "COSINE"
                    }
                )
            ])

    @staticmethod
    async def fetch(url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    return await resp.text()
        except:
            return None

    @staticmethod
    def chunk_text(text, size=500, overlap=50):
        words = text.split()
        return [" ".join(words[i:i+size]) for i in range(0, len(words), size - overlap)]

    def store_in_redis(self, url, chunk):
        vec = self.embedding_model.encode(chunk).astype(np.float32).tobytes()
        doc_id = str(uuid.uuid4())
        self.redis_client.hset(f"doc:{doc_id}", mapping={
            "url": url,
            "chunk": chunk,
            "embedding": vec
        })

    @staticmethod
    def content_hash(text):
        return hashlib.md5(text.encode()).hexdigest()

    async def ingest(self, request: Request):
        data = await request.json()
        urls: List[str] = data.get("urls", [])

        tasks = [self.fetch(url) for url in urls]
        pages = await asyncio.gather(*tasks)

        for url, html in zip(urls, pages):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            hash_val = self.content_hash(text)
            if self.hash_cache.get(url) == hash_val:
                print(f"Skipping unchanged content for {url}")
                continue
            self.hash_cache[url] = hash_val
            for chunk in self.chunk_text(text):
                self.store_in_redis(url, chunk)
            
        self.remove_duplicates()

        return {"message": f"Processed {len(urls)} url(s)"}

    # Semantic Search Endpoint
    async def search(self, request: Request):
        try:
            data = await request.json()
            query = data.get("query", "").strip()
            if not query:
                return {"error": "Query cannot be empty"}, 400

            k = int(data.get("k", 3))

            qvec = await asyncio.to_thread(self.embedding_model.encode, query)
            qvec = qvec.astype(np.float32).tobytes()

            q = Query(f'*=>[KNN {k} @embedding $vec AS score]').return_fields('url', 'chunk', 'score')

            results = self.redis_client.ft("content_index").search(
                q,
                query_params={"vec": qvec},
            )

            results = [
                {"url": d.url, "chunk": d.chunk, "score": float(d.score)}
                for d in results.docs
            ]

            results = sorted(results, key=lambda x: x["score"])

            return results

        except Exception as e:
            return {"error": str(e)}, 500
    
    def remove_duplicates(self, prefix="doc:"):
        """
        Removes documents in Redis with duplicate 'chunk' values.

        Args:
            redis_client: A redis.Redis instance.
            prefix (str): Prefix for document keys (default: "doc:")
        """
        seen_chunks = set()
        deleted_keys = []

        for key in self.redis_client.scan_iter(f"{prefix}*"):
            chunk = self.redis_client.hget(key, "chunk")
            if chunk is None:
                continue  # Skip malformed entries

            if chunk in seen_chunks:
                self.redis_client.delete(key)
                deleted_keys.append(key)
            else:
                seen_chunks.add(chunk)

        print(f"✅ Removed {len(deleted_keys)} duplicate chunk(s).")
        return deleted_keys
    

vector_db = VectorDatabase()
@app.post("/ingest")
async def ingest(request: Request):
    return await vector_db.ingest(request)

@app.post("/search")
async def search(request: Request):
    return await vector_db.search(request)


if __name__ == "__main__":
    uvicorn.run("db:app", port=8001, reload=True)