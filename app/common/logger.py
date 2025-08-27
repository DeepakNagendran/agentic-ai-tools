import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("agentic_ai.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)