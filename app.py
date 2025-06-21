import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from src.common.logger import logger, get_request_id
from src.common.constants import LOGGER_CHAT_ORCHESTRATOR
from src.orchestrator import ChatOrchestrator
from src.request_models import ChatRequest, IngestRequest, SearchRequest
from src.database import VectorDatabase

app = FastAPI()
orchestrator = ChatOrchestrator()
vector_database = VectorDatabase()

@app.post("/process/")
async def process_item(request: ChatRequest):
    setattr(request, 'request_id', get_request_id())
    try:
        orchestrator_response = await orchestrator.process(request)
        return {
            "response": orchestrator_response,
            "error": False
        }
    except Exception as e:
        logger.error(f"{LOGGER_CHAT_ORCHESTRATOR} - {getattr(request, 'request_id', 'N/A')} - Error processing request: {e}")
        return {
            "error": str(e),
            "message": "We are facing some trouble, please try again in some time."
        }

@app.post("/process_stream")
async def process_item_stream(request: ChatRequest):
    setattr(request, 'request_id', get_request_id())
    try:
        orchestrator_response = await orchestrator.process(request, stream=True)
        gathered_chunks = []
        async def format_response():
            # This function will yield chunks of the response
            async for chunk in orchestrator_response:
                if isinstance(chunk, str):
                    gathered_chunks.append(chunk)
                    yield str({"chunk": chunk})+"\n"
                else:
                    yield str({"error": "Invalid response format from orchestrator"})+"\n"
            
            yield str({"final_response": "".join(gathered_chunks)})+"\n"
        return StreamingResponse(format_response(), media_type="text/plain")
    except Exception as e:
        logger.exception(f"{LOGGER_CHAT_ORCHESTRATOR} - {getattr(request, 'request_id', 'N/A')} - Error processing request: {e}")
        return {
            "error": str(e),
            "message": "We are facing some trouble, please try again in some time."
        }

@app.post("/ingest")
async def ingest(request: IngestRequest):
    setattr(request, 'request_id', get_request_id())
    return await vector_database.ingest(request)

@app.post("/search")
async def search(request: SearchRequest):
    setattr(request, 'request_id', get_request_id())
    return await vector_database.search(request)


if __name__ == "__main__":
    # Run the FastAPI app using uvicorn
    uvicorn.run("app:app", port=8000, reload=True)