# processing-service/src/main.py
import logging
import os
import threading
import time
import sys
from dotenv import load_dotenv

from queue_consumer import QueueConsumer
from api.server import start_api_server
from storage.db_manager import get_db_manager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the processing service"""
    max_retries = 5
    retry_delay = 5  # seconds
    attempt = 0
    
    # Initialize database connection manager with retry logic
    db_manager = None
    while attempt < max_retries:
        try:
            db_manager = get_db_manager()
            logger.info("Database connection manager initialized")
            break
        except Exception as e:
            attempt += 1
            logger.error(f"✗ Database connection attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("✗ Max retries reached for database connection. Exiting.")
                sys.exit(1)

    # Reset attempt counter for queue consumer retries
    attempt = 0
    
    # Start the API server in a separate thread
    api_thread = threading.Thread(target=start_api_server)
    api_thread.daemon = True
    api_thread.start()
    logger.info("API server started in background thread")

    # Start the queue consumer with retry logic
    while attempt < max_retries:
        try:
            logger.info(f"\n=== Starting Queue Consumer (Attempt {attempt + 1}/{max_retries}) ===")
            consumer = QueueConsumer()
            consumer.connect()
            consumer.start_consuming()
            break  # If we get here, everything worked
        except Exception as e:
            attempt += 1
            logger.error(f"✗ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("✗ Max retries reached. Exiting.")
                # Close database connections on exit
                db_manager.close()
                logger.info("Database connections closed")
                sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n=== Service Shutdown Requested ===")
        # Close database connections on exit
        get_db_manager().close()
        logger.info("Database connections closed")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n✗ Fatal error: {e}")
        # Close database connections on exit
        get_db_manager().close()
        logger.info("Database connections closed")
        sys.exit(1)