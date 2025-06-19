import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from src.orchestrator import ChatOrchestrator
from src.utils import ChatRequest


app = FastAPI()
orchestrator = ChatOrchestrator()

@app.post("/process/")
async def process_item(request: ChatRequest):
    orchestrator_response = await orchestrator.process(request)
    return {
        "message": "Data received successfully!",
        "output": orchestrator_response
    }

@app.post("/process_stream")
async def process_item(request: ChatRequest):
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

if __name__ == "__main__":
    # Run the FastAPI app using uvicorn
    uvicorn.run(app)