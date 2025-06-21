import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from src.common.logger import logger, get_request_id
from src.common.constants import LOGGER_CHAT_ORCHESTRATOR
from src.orchestrator import ChatOrchestrator
from src.request_models import ChatRequest, IngestRequest, SearchRequest
from src.database import VectorDatabase
import asyncio
from contextlib import asynccontextmanager

# Global instances for shared resources
vector_database = VectorDatabase()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up the application...")
    yield
    # Shutdown
    logger.info("Shutting down the application...")

app = FastAPI(lifespan=lifespan)

@app.post("/process/")
async def process_item(request: ChatRequest):
    setattr(request, 'request_id', get_request_id())
    
    # Create a new orchestrator instance for each request to avoid blocking
    orchestrator = ChatOrchestrator()
    
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
    
    # Create a new orchestrator instance for each request to avoid blocking
    orchestrator = ChatOrchestrator()
    
    try:
        orchestrator_response = await orchestrator.process(request, stream=True)
        gathered_chunks = []
        
        async def format_response():
            # Check if the response is an async generator (streaming) or a dict (error)
            if hasattr(orchestrator_response, '__aiter__'):
                # This is a streaming response
                async for chunk in orchestrator_response:
                    if isinstance(chunk, str):
                        gathered_chunks.append(chunk)
                        yield json.dumps({"chunk": chunk})+"\n"
                    else:
                        yield json.dumps({"error": "Invalid response format from orchestrator"})+"\n"
                
                yield str({"final_response": "".join(gathered_chunks)})+"\n"
            else:
                # This is an error response (dict)
                yield json.dumps(orchestrator_response)+"\n"
        
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

# Health Check Endpoint
@app.get("/health/")
async def health_check():
    try:
        # Perform a simple check to see if the service is running
        return {"status": "ok", "message": "Service is running"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": "Service is not running"}

if __name__ == "__main__":
    # Run the FastAPI app using uvicorn with optimized settings for concurrency
    uvicorn.run(
        "app:app", 
        port=8000, 
        reload=True,
        workers=4,  # Multiple worker processes
        loop="asyncio",
        http="httptools",  # Faster HTTP parser
        access_log=False  # Disable access logs for better performance
    )