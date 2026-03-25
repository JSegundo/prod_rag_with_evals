from typing import Dict
import time
from process_pipeline.extract import TextExtractor
from process_pipeline.chunk import TextChunker
from process_pipeline.embed import TextEmbedder  # We'll create this next
from notifier.notifier import StatusNotifier  # We'll create this next
from storage.db_manager import DatabaseManager, get_db_manager

class DocumentProcessor:
    def __init__(self, db_manager:DatabaseManager):
        """
        Initialize the complete document processing pipeline
         Args:
            db_manager: Database connection manager
        """
        print("\n=== Initializing Document Processor ===")
        try:
            self.db_manager = db_manager
            print("✓ Database manager initialized")
            
            self.extractor = TextExtractor()
            print("✓ Text extractor initialized")
            
            self.chunker = TextChunker()
            print("✓ Text chunker initialized")
            
            self.embedder = TextEmbedder(db_manager)
            print("✓ Text embedder initialized")
            
            self.notifier = StatusNotifier()
            print("✓ Status notifier initialized")
            
            print("✓ Initialized all pipeline components")
            print("=== Initialization Complete ===\n")
        except Exception as e:
            print(f"✗ Failed to initialize DocumentProcessor: {e}")
            import traceback
            traceback.print_exc()
            raise

    def process_document(self,file_id:str, file_path: str, metadata: Dict = None) -> Dict:
        """
        Run the complete document processing pipeline:
        1. Extract text and structure using docling
        2. Chunk the extracted text
        3. Create and store embeddings
        
        Args:
            file_path: Path to the document file
            metadata: Additional document metadata
            
        Returns:
            Dict containing processing results and status
        """
        try:
            print("\n=== Starting Document Processing Pipeline ===")
            print(f"Processing file: {file_path}")
            
               # Notify processing started
            self.notifier.send_notification(file_id, "processing", {
                "stage": "started",
                "timestamp": time.time()
            })

            # Step 1: Extract text using docling
            # Notify processing started
            self.notifier.send_notification(file_id, "processing", {"stage": "extracting"})
            print("Step 1: Extracting text...")
            extracted_data = self.extractor.extract(file_path) # docling
            document = extracted_data['document']
            json_data = extracted_data['json']
                        
            # Step 2: Chunk the text
            self.notifier.send_notification(file_id, "processing", {"stage": "chunking"})
            print("\nStep 2: Chunking text...")
            chunks = self.chunker.chunk_text(document)
            print(f"✓ Created {len(chunks)} chunks")
            
            # Step 3: Create and store embeddings
            self.notifier.send_notification(file_id, "processing", {"stage": "embedding"})
            print("\nStep 3: Creating embeddings...")
            # Combine metadata with document info
            enhanced_metadata = {
                **(metadata or {}),
                'title': json_data.get('title'),
                'document_structure': json_data
            }
            
            processed_chunks = self.embedder.create_embeddings(
                chunks=chunks,
                metadata=enhanced_metadata
            )
            print(f"✓ Created and stored embeddings for {len(processed_chunks)} chunks")
            
            self.notifier.send_notification(file_id, "completed", {
                "chunkCount": len(processed_chunks),
                "ready": True
            })

            print("=== Document Processing Complete ===\n")
            return {
                'status': 'success',
                'document_info': {
                    'title': json_data.get('title'),
                    'num_chunks': len(chunks),
                    'metadata': enhanced_metadata
                }
            }
            
        except Exception as e:
            print(f"✗ Error in document processing pipeline: {e}")
            print("=== Document Processing Failed ===\n")
            self.notifier.send_notification(file_id, "failed", {
                "error": str(e)
            })
            raise