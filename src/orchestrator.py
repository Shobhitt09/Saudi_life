from typing import AsyncGenerator, Literal
from src.utils import ChatRequest
from src.common.constants import LANGUAGE_MAP
from src.common.config import SARVAM_API_KEY, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID, DB_SEARCH_API_URL
from src.common.prompts import LLM_RESPONSE_SYSTEM_PROMPT, LLM_RESPONSE_USER_PROMPT
from src.common.logger import logger
from sarvamai import SarvamAI
from openai import OpenAI
import requests

class ChatOrchestrator:
    def __init__(self):
        self.translator_client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        self.llm_client = OpenAI(
            api_key=LLM_API_KEY, 
            base_url=LLM_BASE_URL
        )

    async def process(self, request: ChatRequest, stream: bool = False):
        logger.info(f"Received request: {request}")
        language = self.identify_language(request.query)
        translated_query = self.translate_query(request.query, language, "en")
        contexts = self.fetch_contexts(translated_query)
        if stream:
            llm_response = self.generate_llm_response_stream(translated_query, contexts, language)
            return llm_response
        
        llm_response = self.generate_llm_response(translated_query, contexts, language)
        return llm_response
    
    def identify_language(self, query: str) -> Literal["hi", "ml"]:
        devanagari_range = range(0x0900, 0x0980)
        malayalam_range = range(0x0D00, 0x0D80)

        devanagari_count = sum(1 for char in query if ord(char) in devanagari_range)
        malayalam_count = sum(1 for char in query if ord(char) in malayalam_range)
        
        identified_language = "hi" if devanagari_count > malayalam_count else "ml"
        logger.info(f"Language identified: {identified_language}")
        
        return identified_language
    
    def translate_query(self, query: str, source_lang: str, target_lang: str) -> str: 
        try:
            response = self.translator_client.text.translate(
                input=query,
                source_language_code=f"{source_lang}-IN",
                target_language_code=f"{target_lang}-IN",
                model="sarvam-translate:v1"
            ).translated_text

            logger.info(f"Translation from {source_lang} to {target_lang} successful: {response}")
            return response
        except Exception as e:
            print(f"Translation error: {e}")
            return None
        
    def fetch_contexts(self, query: str, k: int = 3) -> list:
        url = DB_SEARCH_API_URL
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "query": query,
            "k": k
        }
        # c1 = "Saudi Arabia has been diversifying its economy under the Vision 2030 initiative, leading to growing opportunities in sectors like technology, tourism, construction, renewable energy, and entertainment. Expats and locals alike can explore high-demand roles in fields such as IT, project management, healthcare, and education. The government offers work visas for skilled professionals, and Saudization policies are encouraging more local employment while also promoting sectors open to foreign talent."
        # c2 = "Remote and online income is a growing trend in Saudi Arabia. Residents can earn through freelancing platforms like Upwork or Fiverr, content creation on YouTube or TikTok, affiliate marketing, and e-commerce through platforms like Amazon.sa or Noon. Crypto trading and stock investing (Tadawul market) are also common among tech-savvy individuals. The government supports digital entrepreneurship through programs like Monsha’at and Fintech Saudi, offering support and funding for startups."
        # c3 = "Starting a small business in Saudi Arabia has become easier due to reforms in business licensing, especially for foreigners through the MISA (Ministry of Investment). Profitable ideas include setting up cafes, logistics companies, real estate ventures, digital services, and tourism-related businesses. With a growing middle class and increased consumer spending, Saudi Arabia is an attractive place for investment. Crowdfunding platforms, angel networks, and startup accelerators like Misk and Flat6Labs also support early-stage ventures."
        contexts = requests.post(url, json=data, headers=headers).json()

        logger.info(f"Fetched {len(contexts)} contexts for query")
        return [context['chunk'] for context in contexts]
    
    def generate_llm_response(self, query: str, contexts: list, language: Literal['hi', 'ml']) -> str:
        try:
            response = self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": LLM_RESPONSE_SYSTEM_PROMPT},
                    {"role": "user", "content": LLM_RESPONSE_USER_PROMPT.format(context="\n".join(contexts), query=query, language=language)}
                ],
                model=LLM_MODEL_ID,
            )
            logger.info("LLM response generated successfully")

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM generation error: {e}")
            return None
        
    async def generate_llm_response_stream(self, query: str, contexts: list, language: Literal['hi', 'ml']) -> AsyncGenerator[str, None]:
        response = self.llm_client.chat.completions.create(
            messages=[
                {"role": "system", "content": LLM_RESPONSE_SYSTEM_PROMPT},
                {"role": "user", "content": LLM_RESPONSE_USER_PROMPT.format(context="\n".join(contexts), query=query, language=LANGUAGE_MAP[language])}
            ],
            model=LLM_MODEL_ID,
            stream=True
        )

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

    
