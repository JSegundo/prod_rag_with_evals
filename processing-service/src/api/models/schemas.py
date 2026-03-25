# processing-service/src/api/models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
    
class SearchResult(BaseModel):
    """Result from a vector search"""
    id: int
    document_id: int
    text: str
    score: float
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "document_id": 1,
                "text": "This is a sample text chunk from a document. It contains information that matched the search query.",
                "score": 0.89,
                "metadata": {
                    "filename": "document.pdf",
                    "title": "Section 1",
                    "page_numbers": [1, 2]
                }
            }
        }

class SearchRequest(BaseModel):
    """Request for vector search"""
    query: str
    document_id: Optional[int] = None
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    
    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('query cannot be empty')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "How does the system process documents?",
                "document_id": 1,
                "top_k": 5,
                "min_score": 0.6
            }
        }
    
class SearchResponse(BaseModel):
    """Response from vector search"""
    results: List[SearchResult]
    query: str
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": 1,
                        "document_id": 1,
                        "text": "The system processes documents by first extracting text, then chunking it into smaller pieces, and finally generating vector embeddings for each chunk.",
                        "score": 0.92,
                        "metadata": {
                            "filename": "system_architecture.pdf",
                            "title": "Document Processing Pipeline",
                            "page_numbers": [3]
                        }
                    },
                    {
                        "id": 2,
                        "document_id": 1,
                        "text": "Document processing happens asynchronously through a queue-based system. When a user uploads a document, it's placed in a processing queue.",
                        "score": 0.85,
                        "metadata": {
                            "filename": "system_architecture.pdf",
                            "title": "Queue-Based Processing",
                            "page_numbers": [4]
                        }
                    }
                ],
                "query": "How does the system process documents?",
                "total": 2
            }
        }

# Additional models for future endpoints

class HealthResponse(BaseModel):
    """Response for health check endpoint"""
    status: str
    timestamp: float
    version: Optional[str] = None

class Document(BaseModel):
    """Document metadata"""
    id: int
    filename: str
    created_at: str

class DocumentListResponse(BaseModel):
    """Response for listing documents"""
    documents: List[Document]
    total: int    