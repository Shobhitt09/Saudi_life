import logging
import sys

# Create a custom logger
logger = logging.getLogger("SaudiLifeLogger")
logger.setLevel(logging.DEBUG)  # Set lowest level to capture all logs

# Create handler for stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # You can adjust this if needed

# Formatter
formatter = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
console_handler.setFormatter(formatter)

# Avoid duplicate logs if handler already added
if not logger.hasHandlers():
    logger.addHandler(console_handler)
