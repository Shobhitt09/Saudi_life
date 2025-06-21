from typing import AsyncGenerator, Literal
from sarvamai import SarvamAI
from openai import OpenAI
from fastapi import Request

from src.common.constants import LANGUAGE_MAP, LOGGER_CHAT_ORCHESTRATOR
from src.common.config import SARVAM_API_KEY, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID
from src.common.prompts import LLM_RESPONSE_SYSTEM_PROMPT, LLM_RESPONSE_USER_PROMPT
from src.common.logger import logger
from src.request_models import ChatRequest, SearchRequest
from src.database import VectorDatabase

class ChatOrchestrator:
    def __init__(self):
        self.translator_client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        self.llm_client = OpenAI(
            api_key=LLM_API_KEY, 
            base_url=LLM_BASE_URL
        )
        self.vector_database = VectorDatabase()

    async def process(self, request: ChatRequest, stream: bool = False):
        if not hasattr(request, "query") or not request.query:
            logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request.request_id} - Empty query received")
            return {"error": "Query cannot be empty", "message": "Please provide a valid query."}
        
        logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request.request_id} - Processing request: {request.query}")
        
        language = self.identify_language(request.query, request_id=request.request_id)
        translated_query = self.translate_query(request.query, language, "en", request_id=request.request_id)
        contexts = await self.fetch_contexts(translated_query, k=3, request_id=request.request_id)

        if stream:
            llm_response = self.generate_llm_response_stream(translated_query, contexts, language, request_id=request.request_id)
            return llm_response
        
        llm_response = self.generate_llm_response(translated_query, contexts, language, request_id=request.request_id)
        return llm_response
    
    def identify_language(self, query: str, request_id=None) -> Literal["en", "hi", "ml"]:
        english_range = range(0x0041, 0x007F)
        devanagari_range = range(0x0900, 0x0980)
        malayalam_range = range(0x0D00, 0x0D80)

        english_count = sum(1 for char in query if ord(char) in english_range)
        devanagari_count = sum(1 for char in query if ord(char) in devanagari_range)
        malayalam_count = sum(1 for char in query if ord(char) in malayalam_range)

        count_map = {"en": english_count, "hi": devanagari_count, "ml": malayalam_count}
        identified_language = sorted(count_map.items(), key=lambda x: x[1], reverse=True)[0][0]
        logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Identified language: {identified_language} for query: {query}")
        
        return identified_language
    
    def translate_query(self, query: str, source_lang: str, target_lang: str, request_id=None) -> str: 
        if source_lang == target_lang:
            logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - No translation needed for {source_lang} to {target_lang}")
            return query
        try:
            response = self.translator_client.text.translate(
                input=query,
                source_language_code=f"{source_lang}-IN",
                target_language_code=f"{target_lang}-IN",
                model="sarvam-translate:v1"
            ).translated_text

            logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Translation from {source_lang} to {target_lang} successful: {response}")
            return response
        except Exception as e:
            logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Translation error: {e}")
            return None
        
    async def fetch_contexts(self, query: str, k: int = 3, request_id=None) -> list:
        search_request = SearchRequest(query=query, k=k, request_id=request_id)
        contexts = await self.vector_database.search(search_request)
        if not contexts:
            logger.warning(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - No contexts found for query: {query}")
            return []

        logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Fetched {len(contexts)} contexts for query: {query}")
        return [context['chunk'] for context in contexts]
    
    def generate_llm_response(self, query: str, contexts: list, language: Literal['hi', 'ml'], request_id=None) -> str:
        try:
            response = self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": LLM_RESPONSE_SYSTEM_PROMPT},
                    {"role": "user", "content": LLM_RESPONSE_USER_PROMPT.format(context="\n".join(contexts), query=query, language=language)}
                ],
                model=LLM_MODEL_ID,
            )
            logger.info(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - LLM response generated successfully")

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {request_id} - Error generating LLM response: {e}")
            return None
        
    async def generate_llm_response_stream(self, query: str, contexts: list, language: Literal['hi', 'ml'], request_id=None) -> AsyncGenerator[str, None]:
        response = self.llm_client.chat.completions.create(
            messages=[
                {"role": "system", "content": LLM_RESPONSE_SYSTEM_PROMPT},
                {"role": "user", "content": LLM_RESPONSE_USER_PROMPT.format(context="\n".join(contexts), query=query, language=LANGUAGE_MAP[language])}
            ],
            model=LLM_MODEL_ID,
            stream=True
        )
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
            
    
if __name__ == "__main__":
    orchestrator = ChatOrchestrator()
    hindi_lid = orchestrator.identify_language("नमस्ते, आप कैसे हैं?")  # Example usage
    malayalam_lid = orchestrator.identify_language("നമസ്കാരം, നിങ്ങൾ എങ്ങനെയുണ്ട്?")  # Example usage
    assert hindi_lid == "hi", "Expected Hindi language identifier"
    assert malayalam_lid == "ml", "Expected Malayalam language identifier"

    translate_result = orchestrator.translate_query("नमस्ते, आप कैसे हैं?", "hi", "en")
    print(f"Translation Result: {translate_result}")  # Example usage

    
