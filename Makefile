# Variables
APP_MODULE=app:app
PORT=8000
HOST=0.0.0.0
RELOAD=true

# Create virtual environment and install dependencies
install:
	@echo "Setting up virtual environment and installing dependencies..."
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Run FastAPI app using uvicorn
run:
	@echo "Starting SaudiLife app..."
	if [ "$(RELOAD)" = "true" ]; then
		UVICORN_CMD="uvicorn --reload"
	else
		UVICORN_CMD="uvicorn"
	fi
	. .venv/bin/activate && $(UVICORN_CMD) $(APP_MODULE) --host $(HOST) --port $(PORT) --workers 4

# Clean up
clean:
	@echo "Cleaning up temporary files..."
	rm -rf __pycache__ .pytest_cache .venv *.pyc

test:
	@echo "Running tests..."
	. .venv/bin/activate && pytest -v tests/*.py

# Help
help:
	@echo "Available commands:"
	@echo "  install     Set up virtual environment and install dependencies"
	@echo "  run         Run FastAPI app using Uvicorn"
	@echo "  clean       Remove temporary files"
