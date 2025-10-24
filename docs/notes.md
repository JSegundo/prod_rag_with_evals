pdf-parse for server
https://www.npmjs.com/package/pdf-parse

pdf-lib client
https://www.npmjs.com/package/pdf-lib

├── api-server/                  # Node.js API Server
│   ├── src/
│   │   ├── routes/             # API endpoints
│   │   │   ├── chat.ts        # Chat endpoints
│   │   │   └── documents.ts    # Document upload endpoints
│   │   ├── services/
│   │   │   ├── chat/          # Chat-related services
│   │   │   │   ├── manager.ts # Orchestrates chat flow
│   │   │   │   └── history.ts # Manages chat history
│   │   │   └── documents/     # Document-related services
│   │   ├── websocket/         # WebSocket handlers
│   │   └── queue/             # Queue producers
│   └── config/
│
├── processing-service/          # Python Processing Service
│   ├── src/
│   │   ├── pipeline/          # Document processing pipeline
│   │   │   ├── processor.py   # PDF/Doc extraction
│   │   │   ├── chunker.py     # Text chunking
│   │   │   └── embedder.py    # Embedding generation
│   │   ├── rag/               # RAG components
│   │   │   ├── context.py     # Context building
│   │   │   ├── search.py      # Vector search
│   │   │   └── rerank.py      # Result reranking
│   │   └── queue/             # Queue consumers
│   └── config/
│
└── shared/                      # Shared configurations/types



# Key Design Decisions:

## Asynchronous Processing: 
    Long-running tasks (PDF processing, embedding generation) happen asynchronously through message queues.
    Stateless Services:
        Both Node.js and Python services are stateless, making them easy to scale.
    
    Shared Resources:
        Vector DB accessible by both services
        File storage (S3/similar) for document storage
        Message queue for communication
        Redis for caching frequent queries


## Responsibility Split:
    Node.js handles:
        API endpoints, auth, file uploads, chat orchestration
    Python handles: 
        Document processing, chunking, embedding generation




# Key Components Explained:
# Key Components Explained:
# Key Components Explained:
# Key Components Explained:

## Chat Flow (buildContext expanded):

User sends message via WebSocket
### Chat Flow (buildContext expanded):

    User sends message via WebSocket
    Chat Manager:

    Retrieves conversation history
    Gets relevant chunks from Vector Search
    Context Builder combines:

    Most relevant document chunks
    Recent conversation history
    System prompts/instructions

        Optional: Reranker fine-tunes relevance
        Formats final prompt for LLM
        Streams response back via WebSocket


### Document Processing Flow:

    Upload → File Storage
    Queue job for processing
    Python service:

    Extracts text
    Splits into optimal chunks
    Generates embeddings
    Stores in Vector DB with metadata


### Performance Optimizations:

    Cache frequent vector searches
    Batch embedding generations
    Stream responses for better UX
    Reuse WebSocket connections


### Scalability Points:

    Separate queues for different processing types
    Independent scaling of Node.js and Python services
    Cache sharing between services
    Stateless design for horizontal scaling


#### This architecture allows for:

Real-time chat with streamed responses
Asynchronous document processing
Efficient context retrieval and reranking
Scalable processing of large documents
Easy addition of new document types or LLM providers


# Communication:
# Communication:
Use Message Queue (RabbitMQ/Redis) for:
    Document processing
    Embedding generation
    Any long-running tasks

Use HTTP/REST for:
    Vector searches
    Context retrieval
    Real-time operations

Optional: Use WebSocket between services for:
    Stream processing updates
    Real-time notifications







### nice to 

Performance Optimizations:
    Cache frequent vector searches
    Batch embedding generations
    Stream responses for better UX
    Reuse WebSocket connections

Scalability Points:
    Separate queues for different processing types
    Independent scaling of Node.js and Python services
    Cache sharing between services
    Stateless design for horizontal scaling

This architecture allows for:
    Real-time chat with streamed responses
    Asynchronous document processing
    Efficient context retrieval and reranking
    Scalable processing of large documents
    Easy addition of new document types or LLM providers



    CONSIERING THAT DOCLING IS VERY CPU INTENSIVE, IS THERE ANY DEPLOYMENT / SCALABILITY CONFIGURATIONS THAT WE MIGHT WANT TO HAVE?

// problemas:
// problemas:
// problemas:

## monitor memory usage 
### Check overall Docker disk usage
docker system df
### More detailed view with actual sizes
docker system df -v
### Check disk space on your entire system
df -h

bugs happen when uploading large documents (200 pages book) docling gets stuck, rabbit closes connection and websockets too.
    
processing-service getting stuck 
    - takes long to loadwhen downloading OCRmodels
        easyocr.easyocr - WARNING - Downloading detection model, please wait.

// chunks: 0 ?