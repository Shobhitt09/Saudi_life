# Variables
APP_MODULE=app:app
PORT=8000
HOST=0.0.0.0
RELOAD=true
DB_MODULE=db:app
DB_PORT=8001

# Create virtual environment and install dependencies
install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Run FastAPI app using uvicorn
run:
	. .venv/bin/activate && uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

db:
	. .venv/bin/activate && uvicorn $(DB_MODULE) --host $(HOST) --port $(DB_PORT) --reload

# Clean up
clean:
	rm -rf __pycache__ .pytest_cache .venv *.pyc

# Help
help:
	@echo "Available commands:"
	@echo "  install     Set up virtual environment and install dependencies"
	@echo "  run         Run FastAPI app using Uvicorn"
	@echo "  db          Run FastAPI app for database operations using Uvicorn"
	@echo "  clean       Remove temporary files"
