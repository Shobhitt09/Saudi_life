# Variables
APP_MODULE=app:app
PORT=8000
HOST=0.0.0.0
RELOAD=true

# Create virtual environment and install dependencies
install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Run FastAPI app using uvicorn
run:
	. .venv/bin/activate && uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

# Clean up
clean:
	rm -rf __pycache__ .pytest_cache .venv *.pyc

# Help
help:
	@echo "Available commands:"
	@echo "  install     Set up virtual environment and install dependencies"
	@echo "  run         Run FastAPI app using Uvicorn"
	@echo "  clean       Remove temporary files"
