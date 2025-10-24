# processing-service/src/process_pipeline/embed.py
import os
import json
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

from storage.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TextEmbedder:
    """Generates and stores embeddings for text chunks"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the embedder with OpenAI client and database manager
        
        Args:
            db_manager: Database connection manager
        """
        try:
            # Store the database manager
            self.db_manager = db_manager
            
            # Initialize OpenAI client
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("OPENAI_API_KEY environment variable not set")
                raise ValueError("OPENAI_API_KEY environment variable not set")
                
            logger.info(f"Initializing OpenAI client with API key: {api_key[:10]}...")
            self.client = OpenAI(api_key=api_key)
            logger.info("Text embedder initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TextEmbedder: {e}", exc_info=True)
            raise
    
    def create_embeddings(self, chunks: List, metadata: Dict = None) -> List[Dict]:
        """
        Create embeddings for text chunks and store them in PostgreSQL with pgvector.
        
        Args:
            chunks: A list of DocChunk objects. Each DocChunk contains text and metadata.
            metadata: Additional metadata for the document (optional).
            
        Returns:
            A list of dictionaries, where each dictionary represents a processed chunk.
        """
        if not chunks:
            raise ValueError("The chunks list is empty.")
        
        # First, create a document record in the database
        document_id = self._create_document_record(metadata.get('filename'))
        
        # Process chunks into a structured format
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            # Generate embeddings for the chunk text
            response = self.client.embeddings.create(
                model="text-embedding-3-large",
                input=chunk.text,
                dimensions=1536
            )
            embedding = response.data[0].embedding  # Get the embedding vector
            
            # Prepare the chunk data for insertion
            processed_chunk = {
                "document_id": document_id,
                "chunk_text": chunk.text,
                "embedding": embedding,
                "page_numbers": sorted(
                    set(
                        prov.page_no
                        for item in chunk.meta.doc_items
                        for prov in item.prov
                    )
                )
                or None,
                "metadata": {
                    "filename": chunk.meta.origin.filename,
                    "title": chunk.meta.headings[0] if chunk.meta.headings else None,
                },
            }
            processed_chunks.append(processed_chunk)
        
        # Insert the processed chunks into the database
        self._store_chunks(processed_chunks)
        
        return processed_chunks
    
    def _create_document_record(self, filename: str) -> int:
        """
        Create a new document record in the database
        
        Args:
            filename: The filename of the document
            
        Returns:
            The ID of the newly created document
        """
        sql = 'INSERT INTO documents (filename) VALUES (%s) RETURNING id'
        result = self.db_manager.execute_query(sql, (filename,), fetch_one=True)
        return result
    
    def _store_chunks(self, processed_chunks: List[Dict]) -> None:
        """
        Store processed chunks in the database
        
        Args:
            processed_chunks: List of processed chunk data
        """
        try:
            # Prepare the data for insertion
            data = [
                (
                    chunk["document_id"],
                    chunk["chunk_text"],
                    chunk["embedding"],
                    chunk["page_numbers"],
                    json.dumps(chunk["metadata"])
                )
                for chunk in processed_chunks
            ]
            
            # Connect to the database
            conn = self.db_manager.get_connection()
            
            try:
                # Use execute_values for efficient bulk insertion
                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        '''
                        INSERT INTO chunks 
                        (document_id, chunk_text, embedding, page_numbers, metadata)
                        VALUES %s
                        ''',
                        data
                    )
                # Commit the transaction
                conn.commit()
                logger.info(f"Successfully stored {len(processed_chunks)} chunks")
            except Exception as e:
                # Rollback the transaction in case of an error
                conn.rollback()
                logger.error(f"Error adding chunks to database: {e}", exc_info=True)
                raise
            finally:
                # Return the connection to the pool
                self.db_manager.return_connection(conn)
        except Exception as e:
            logger.error(f"Error in _store_chunks: {e}", exc_info=True)
            raise