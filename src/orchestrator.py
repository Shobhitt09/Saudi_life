import base64
import io
from typing import AsyncGenerator, Literal, Optional, Union
from sarvamai import SarvamAI
from openai import OpenAI
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.common.constants import LANGUAGE_MAP, LOGGER_CHAT_ORCHESTRATOR
from src.common.config import SARVAM_API_KEY, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID
from src.common.prompts import LLM_RESPONSE_SYSTEM_PROMPT, LLM_RESPONSE_USER_PROMPT
from src.common.logger import logger
from src.request_models import ChatRequest, SearchRequest
from src.database import VectorDatabase

class ChatOrchestrator:
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
        self.translator_client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        self.llm_client = OpenAI(
            api_key=LLM_API_KEY, 
            base_url=LLM_BASE_URL
        )
        self.vector_database = VectorDatabase()
        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def process(self, request: ChatRequest, stream: bool = False) -> Union[dict[str, str], AsyncGenerator[str, None]]:
        if hasattr(request, "audio") and request.audio:
            audio_bytes = base64.b64decode(request.audio)
            speech_to_text_result, language = await self.speech_to_text(audio_bytes, request_id=request.request_id)
            if speech_to_text_result is None:
                return {"error": "Speech to text failed", "message": "Could not process audio input."}
            request.query = speech_to_text_result
            request.translated_query = speech_to_text_result

        if not hasattr(request, "query") or not request.query:
            logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request.request_id} - Empty query received")
            return {"error": "Query cannot be empty", "message": "Please provide a valid query."}
        
        logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request.request_id} - Processing request: {request.query}")
        
        if not hasattr(request, "audio") or not request.audio:
            language = await self.identify_language(request.query, request_id=request.request_id)
            request.translated_query = await self.translate_query(request.query, language, "en", request_id=request.request_id)
            if request.translated_query is None:
                return {"error": "Translation failed", "message": "Could not translate the query."}

        contexts = await self.fetch_contexts(request.translated_query, k=3, request_id=request.request_id)

        if stream:
            # Cast language to the expected type for streaming
            lang_for_stream = language if language in ['hi', 'ml'] else 'hi'
            llm_response = self.generate_llm_response_stream(request.translated_query, contexts, lang_for_stream, request_id=request.request_id)
            return llm_response
        
        # Cast language to the expected type for non-streaming
        lang_for_llm = language if language in ['hi', 'ml'] else 'hi'
        llm_response = await self.generate_llm_response(request.translated_query, contexts, lang_for_llm, request_id=request.request_id)
        if llm_response is None:
            return {"error": "LLM response generation failed", "message": "Could not generate response."}
        return {"response": llm_response, "error": "false"}
    
    async def speech_to_text(self, audio: bytes, request_id: Optional[str] = None) -> Optional[tuple[str, str]]:
        try:
            # Run the blocking API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.translator_client.speech_to_text.translate(
                    file=audio,
                    model="saaras:v2.5"
                )
            )
            if response and hasattr(response, 'language_code') and hasattr(response, 'transcript'):
                logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Detected Language {response.language_code}. Speech to text translation successful")
                return response.transcript, response.language_code[:2]
            else:
                logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Invalid response from speech to text API")
                return None
        except Exception as e:
            logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Error during speech to text translation: {e}")
            return None
    
    async def identify_language(self, query: str, request_id: Optional[str] = None) -> Literal["en", "hi", "ml"]:
        # Run CPU-intensive language detection in thread pool
        loop = asyncio.get_event_loop()
        identified_language = await loop.run_in_executor(
            self.executor,
            self._identify_language_sync,
            query
        )
        logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Identified language: {identified_language} for query: {query}")
        # Cast to the expected literal type
        if identified_language in ["en", "hi", "ml"]:
            return identified_language
        return "en"  # Default fallback
    
    def _identify_language_sync(self, query: str) -> str:
        english_range = range(0x0041, 0x007F)
        devanagari_range = range(0x0900, 0x0980)
        malayalam_range = range(0x0D00, 0x0D80)

        english_count = sum(1 for char in query if ord(char) in english_range)
        devanagari_count = sum(1 for char in query if ord(char) in devanagari_range)
        malayalam_count = sum(1 for char in query if ord(char) in malayalam_range)

        count_map = {"en": english_count, "hi": devanagari_count, "ml": malayalam_count}
        identified_language = sorted(count_map.items(), key=lambda x: x[1], reverse=True)[0][0]
        return identified_language
    
    async def translate_query(self, query: str, source_lang: str, target_lang: str, request_id: Optional[str] = None) -> Optional[str]: 
        if source_lang == target_lang:
            logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - No translation needed for {source_lang} to {target_lang}")
            return query
        try:
            # Run the blocking API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.translator_client.text.translate(
                    input=query,
                    source_language_code=f"{source_lang}-IN",
                    target_language_code=f"{target_lang}-IN",
                    model="sarvam-translate:v1"
                ).translated_text
            )

            logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Translation from {source_lang} to {target_lang} successful: {response}")
            return response
        except Exception as e:
            logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Translation error: {e}")
            return None
        
    async def fetch_contexts(self, query: str, k: int = 3, request_id: Optional[str] = None) -> list:
        search_request = SearchRequest(query=query, k=k, request_id=request_id)
        contexts = await self.vector_database.search(search_request)
        if not contexts or isinstance(contexts, (int, str)):  # Handle error responses
            logger.warning(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - No contexts found for query: {query}")
            return []

        logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Fetched {len(contexts)} contexts for query: {query}")
        return [context['chunk'] for context in contexts if isinstance(context, dict) and 'chunk' in context]
    
    async def generate_llm_response(self, query: str, contexts: list, language: Literal['hi', 'ml'], request_id: Optional[str] = None) -> Optional[str]:
        try:
            # Run the blocking API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.llm_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": LLM_RESPONSE_SYSTEM_PROMPT},
                        {"role": "user", "content": LLM_RESPONSE_USER_PROMPT.format(context="\n".join(contexts), query=query, language=language)}
                    ],
                    model=LLM_MODEL_ID,
                )
            )
            logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - LLM response generated successfully")

            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as e:
            logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Error generating LLM response: {e}")
            return None
        
    async def generate_llm_response_stream(self, query: str, contexts: list, language: Literal['hi', 'ml'], request_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        # For streaming, we need to run the API call in a thread and yield results
        loop = asyncio.get_event_loop()
        
        def create_stream():
            return self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": LLM_RESPONSE_SYSTEM_PROMPT},
                    {"role": "user", "content": LLM_RESPONSE_USER_PROMPT.format(context="\n".join(contexts), query=query, language=LANGUAGE_MAP[language])}
                ],
                model=LLM_MODEL_ID,
                stream=True
            )
        
        response = await loop.run_in_executor(self.executor, create_stream)
        logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Streaming LLM response for query: {query}")
        
        for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                content = chunk.choices[0]
                if hasattr(content, 'delta') and hasattr(content.delta, 'content'):
                    content = content.delta.content
                else:
                    content = None
                if content:
                    yield content
