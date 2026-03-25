# processing-service/src/queue_consumer.py
import pika
import json
import os
import logging
from dotenv import load_dotenv
from process_pipeline.processor import DocumentProcessor
from storage.db_manager import get_db_manager, DatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class QueueConsumer:
    def __init__(self):
        """Initialize the queue consumer"""
        logger.info("\n=== Initializing Queue Consumer ===")
        
        # Queue setup
        self.connection = None
        self.channel = None
        self.queue_name = os.getenv('RABBITMQ_QUEUE_NAME', 'document_processing')
        self.rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://localhost:5672')
        
        # Get the database manager
        self.db_manager = get_db_manager()
        
        # Initialize document processor with dependency injection
        self.processor = DocumentProcessor(self.db_manager)
        
        # File paths
        self.uploads_dir = os.path.abspath(os.getenv('UPLOADS_DIR', '../server/uploads'))
        
        logger.info(f"Configuration:")
        logger.info(f"- Queue Name: {self.queue_name}")
        logger.info(f"- RabbitMQ URL: {self.rabbitmq_url}")
        logger.info(f"- Upload Directory: {self.uploads_dir}")
        logger.info("=== Initialization Complete ===\n")

    def connect(self):
        """Connect to RabbitMQ"""
        try:
            logger.info("\n=== Connecting to RabbitMQ ===")
            params = pika.URLParameters(self.rabbitmq_url)
            # Disable heartbeat so long-running document processing
            # doesn't cause RabbitMQ to drop the connection
            params.heartbeat = 0
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            # Ensure queue exists
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            logger.info("✓ Successfully connected to RabbitMQ")
        except Exception as e:
            logger.error(f"✗ Error connecting to RabbitMQ: {e}")
            raise

    def process_message(self, ch, method, properties, body):
        """Process a message from the queue"""
        try:
            logger.info("\n=== Processing New Message ===")
            data = json.loads(body)
            logger.info(f"Received message data: {data}")

            # Extract message data
            job_id = data.get('jobId')
            file_path = data.get('filePath')
            retries = data.get('retries', 0)
            metadata = data.get('metadata', {})

            logger.info(f"- Job ID: {job_id}")
            logger.info(f"- Original File Path: {file_path}")
            logger.info(f"- Retry Attempt: {retries}")

            # Validate required fields
            if not all([job_id, file_path]):
                logger.error("✗ Missing required fields - rejecting message")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Check max retries
            if retries >= 3:
                logger.error("✗ Max retries reached - rejecting message")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Get full file path
            file_name = os.path.basename(file_path)
            full_path = os.path.join(self.uploads_dir, file_name)
            logger.info(f"- Full File Path: {full_path}")
            
            # Add job info to metadata
            metadata.update({
                'job_id': job_id,
                'original_filename': file_name
            })
            
            # Process document through pipeline
            result = self.processor.process_document(
                file_id=job_id,
                file_path=full_path,
                metadata=metadata
            )
            
            logger.info(f"✓ Document processing complete:")
            logger.info(f"  - Title: {result['document_info']['title']}")
            logger.info(f"  - Chunks: {result['document_info']['num_chunks']}")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info("✓ Message acknowledged")
            logger.info("=== Message Processing Complete ===\n")

        except Exception as e:
            logger.error(f"✗ Error processing message: {e}")
            # Handle retries
            data['retries'] = retries + 1
            if retries < 3:
                logger.warning(f"✗ Retrying message (attempt {retries + 1}/3)")
                self.channel.basic_publish(
                    exchange='',
                    routing_key=self.queue_name,
                    body=json.dumps(data)
                )
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            logger.error("✗ Original message rejected")
            logger.error("=== Message Processing Failed ===\n")

    def start_consuming(self):
        """Start consuming messages from the queue"""
        try:
            logger.info("\n=== Starting Consumer ===")
            # Set how many messages to process at once
            self.channel.basic_qos(prefetch_count=1)
            logger.info("✓ QoS prefetch set to 1")
            
            # Start consuming messages from the queue
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message
            )
            logger.info(f"✓ Consuming from queue: {self.queue_name}")
            logger.info("=== Consumer Ready ===\n")
            
            logger.info("Waiting for messages... (Press CTRL+C to exit)")
            # Start the consumer (blocks the thread until stopped)
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("\n=== Shutting Down Consumer ===")
            self.channel.stop_consuming()
        finally:
            if self.connection:
                self.connection.close()
                logger.info("✓ Connection closed")
                logger.info("=== Shutdown Complete ===\n")