from functools import lru_cache
import hashlib
import uuid
import asyncio
import aiohttp
import redis
import nltk
import numpy as np

from typing import List
from fastapi import FastAPI
from bs4 import BeautifulSoup
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer
from nltk.tokenize import sent_tokenize

from src.common.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
from src.common.constants import LOGGER_DB_INGEST, LOGGER_DB_SEARCH
from src.common.logger import logger
from src.request_models import IngestRequest, SearchRequest

nltk.download('punkt_tab')

app = FastAPI()

class VectorDatabase:
    def __init__(self):
        self.embedding_model = self.get_embedding_model()
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
    
    @lru_cache()
    def get_embedding_model(self):
        return SentenceTransformer("all-MiniLM-L6-v2")

    @staticmethod
    async def fetch(url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    return await resp.text()
        except:
            return None

    @staticmethod
    def chunk_text(text, max_chars=500, overlap=100):
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = []

        total_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If adding this sentence exceeds the limit, start a new chunk
            if total_length + sentence_len > max_chars:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap from previous
                if overlap > 0 and chunks:
                    prev = chunks[-1]
                    overlap_text = prev[-overlap:]  # last X characters
                    current_chunk = [overlap_text.strip(), sentence]
                    total_length = len(overlap_text) + sentence_len
                else:
                    current_chunk = [sentence]
                    total_length = sentence_len
            else:
                current_chunk.append(sentence)
                total_length += sentence_len

        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    async def store_in_redis(self, chunk):
        vec = self.embedding_model.encode(chunk).astype(np.float32).tobytes()
        doc_id = str(uuid.uuid4())
        self.redis_client.hset(f"doc:{doc_id}", mapping={
            "chunk": chunk,
            "embedding": vec
        })

    @staticmethod
    def content_hash(text):
        return hashlib.md5(text.encode()).hexdigest()

    async def ingest(self, request: IngestRequest):
        logger.info(f"{LOGGER_DB_INGEST} - {request.request_id} - Entered DB Ingest Endpoint")
        urls: List[str] = request.urls or []
        texts: List[str] = request.texts or []

        if not urls and not texts:
            logger.error(f"{LOGGER_DB_INGEST} - {request.request_id} - No URLs or texts provided for ingestion")
            return {"error": "No URLs or texts provided"}, 400
        
        if urls:
            texts = []
            tasks = [self.fetch(url) for url in urls]
            pages = await asyncio.gather(*tasks)

            for url, html in zip(urls, pages):
                if not html:
                    logger.warning(f"{LOGGER_DB_INGEST} - {request.request_id} - Failed to fetch {url}.")
                    continue
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                hash_val = self.content_hash(text)
                if self.hash_cache.get(url) == hash_val:
                    print(f"Skipping unchanged content for {url}")
                    continue
                self.hash_cache[url] = hash_val
                texts.append(text)
        
        for text in texts:
            for chunk in self.chunk_text(text):
                await self.store_in_redis(chunk)
            
        await self.remove_duplicates(request)
        logger.info(f"{LOGGER_DB_INGEST} - {request.request_id} - Ingested {len(texts)} chunk(s)")

        return {"message": f"Processed {len(texts)} chunk(s)"}

    # Semantic Search Endpoint
    async def search(self, request: SearchRequest):
        logger.info(f"{LOGGER_DB_SEARCH} - {request.request_id} - Entered DB Search Endpoint")
        try:
            query = request.query.strip()
            if not query:
                logger.error(f"{LOGGER_DB_SEARCH} - {request.request_id} - Empty query provided for search")
                return {"error": "Query cannot be empty"}, 400

            k = int(request.k) if request.k else 3

            logger.info(f"{LOGGER_DB_SEARCH} - {request.request_id} - Searching for query: {query} with k={k}")

            qvec = await asyncio.to_thread(self.embedding_model.encode, query)
            qvec = qvec.astype(np.float32).tobytes()

            q = Query(f'*=>[KNN {k} @embedding $vec AS score]').return_fields('url', 'chunk', 'score')

            results = self.redis_client.ft("content_index").search(
                q,
                query_params={"vec": qvec},
            )

            results = [
                {"chunk": d.chunk, "score": float(d.score)}
                for d in results.docs
            ]

            results = sorted(results, key=lambda x: x["score"])

            logger.info(f"{LOGGER_DB_SEARCH} - {request.request_id} - Found {len(results)} results for query: {query}")

            return results

        except Exception as e:
            logger.error(f"{LOGGER_DB_SEARCH} - {request.request_id} - Error during search: {str(e)}")
            return {"error": str(e)}, 500
    
    async def remove_duplicates(self, request, prefix="doc:"):
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

        logger.info(f"{LOGGER_DB_INGEST} - {request.request_id} - Removed {len(deleted_keys)} duplicate chunks from Redis")
        logger.info(f"{LOGGER_DB_INGEST} - {request.request_id} - Total unique chunks remaining: {len(seen_chunks)}")
        return deleted_keys

