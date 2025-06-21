# SaudiLife - Multilingual AI Chat Application

A high-performance, multilingual AI chat application that supports speech-to-text, text translation, and contextual responses in multiple languages including English, Hindi, and Malayalam.

## Features
- **Multilingual Support**: English, Hindi, and Malayalam with 
- **Speech-to-Text**: Audio input processing with automatic language detection
- **Text Translation**: Seamless translation between supported languages
- **Contextual Responses**: AI-powered responses based on relevant context
- **Streaming Support**: Real-time streaming responses
- **Vector Search**: Semantic search for context retrieval

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │ ChatOrchestrator │    │ VectorDatabase  │
│                 │    │                  │    │                 │
│ - Request       │───▶│ - Speech-to-Text │    │ - Context Search│
│   Handling      │    │ - Translation    │    │ - Data Ingestion│
│ - Streaming     │    │ - LLM Response   |    │                 │
│   Responses     │    │ - Thread Pool    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd saudilife
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   SARVAM_API_KEY=<your_sarvam_api_key>
   LLM_API_KEY=<your_openai_api_key>
   LLM_BASE_URL=<your_openai_base_url>
   LLM_MODEL_ID=<model_id>
   ```

## 🚀 Quick Start

1. **Start the server**
   ```bash
   python app.py
   ```
   The server will start on `http://localhost:8000`

2. **Test the health endpoint**
   ```bash
   curl http://localhost:8000/health/
   ```

3. **Send a chat request**
   ```bash
   curl -X POST "http://localhost:8000/process/" \
        -H "Content-Type: application/json" \
        -d '{
          "query": "Hello, how are you?"
        }'
   ```

4. **Check the Postman Collection**
Import the postman collection at `saudilife.postman_collection.json`

## 📚 API Endpoints

### 1. Process Chat Request
**POST** `/process/`

Process a text-based chat request with translation and contextual response.

**Request Body:**
```json
{
  "name": "Your Name",
  "query": "Your question here",
  "audio": "base64_encoded_audio" // one of the two
}
```

**Response:**
```json
{
  "response": "AI generated response",
  "error": false
}
```

### 2. Process Chat Request (Streaming)
**POST** `/process_stream`

Process a chat request with real-time streaming response.

**Request Body:** Same as `/process/`

**Response:** Streaming JSON chunks:
```json
{"chunk": "partial response"}
{"chunk": "more response"}
{"final_response": "complete response"}
```

### 3. Ingest Data
**POST** `/ingest`

Add new data to the vector database for context retrieval.

**Request Body:**
```json
{
  "texts": [
    "Text 1 to ingest",
    "Text 2 to ingest"
  ],
  "urls": [
    "url 1 to scrape and ingest",
    "url 2 to scrape and ingest",
  ] // one of the two
}
```

### 4. Search Context
**POST** `/search`

Search for relevant context in the vector database.

**Request Body:**
```json
{
  "query": "Search query",
  "k": 3,
}
```

### 5. Health Check
**GET** `/health/`

Check if the service is running.

**Response:**
```json
{
  "status": "ok",
  "message": "Service is running"
}
```

## 📁 Project Structure

```
saudilife/
├── app.py                 # FastAPI application entry point
├── requirements.txt       # Python dependencies
├── Makefile              # Build and deployment commands
├── src/
│   ├── common/
│   │   ├── config.py     # Configuration management
│   │   ├── constants.py  # Application constants
│   │   ├── logger.py     # Logging configuration
│   │   └── prompts.py    # LLM prompts
│   ├── database.py       # Vector database operations
│   ├── orchestrator.py   # Main chat orchestration logic
│   └── request_models.py # Pydantic request models
└── tests/
    ├── example.wav       # Test audio file
    ├── example.wav.base64 # Base64 encoded test audio
    ├── test-process.py   # Process endpoint tests
    └── test-process-stream.py # Streaming endpoint tests
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
