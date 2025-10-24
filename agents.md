# AI Assistant Guide for PDF-RAG Project

This document provides comprehensive information for AI assistants working with the PDF-RAG codebase. It contains technical details, architecture patterns, and development guidelines.

## 🏗️ System Architecture

### Service Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │   Node.js       │    │   Python        │
│   Client        │◄──►│   API Server    │◄──►│   Processing    │
│   (Port 3500)   │    │   (Port 3000)   │    │   Service       │
└─────────────────┘    └─────────────────┘    │   (Port 8000)   │
                              │                └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   RabbitMQ      │◄──►│   PostgreSQL    │
                    │   (Message      │    │   + pgvector    │
                    │    Queue)       │    └─────────────────┘
                    └─────────────────┘
```

### Data Flow
1. **Upload**: Client → API Server → RabbitMQ Queue
2. **Processing**: RabbitMQ → Processing Service → PostgreSQL
3. **Chat**: Client → API Server → Processing Service → LLM → Client

## 📁 Project Structure

```
pdf-RAG/
├── client/                    # Next.js frontend
│   ├── src/app/
│   │   ├── components/        # React components
│   │   │   ├── PDFDropzone.tsx
│   │   │   ├── ProcessingStatus.tsx
│   │   │   └── ui/           # Reusable UI components
│   │   ├── utils/            # Utility functions
│   │   └── page.tsx          # Main page
│   └── package.json
├── server/                   # Node.js API server
│   ├── src/
│   │   ├── api/
│   │   │   ├── controllers/  # Request handlers
│   │   │   └── routes/       # API endpoints
│   │   ├── services/
│   │   │   ├── chat/         # Chat management
│   │   │   ├── llm/          # LLM providers
│   │   │   ├── queue/        # Message queue
│   │   │   └── websocket/    # WebSocket handling
│   │   ├── middleware/       # Express middleware
│   │   ├── types/           # TypeScript types
│   │   └── index.ts         # Server entry point
│   └── package.json
├── processing-service/       # Python processing service
│   ├── src/
│   │   ├── api/             # FastAPI endpoints
│   │   ├── process_pipeline/ # Document processing
│   │   │   ├── extract.py   # Text extraction (Docling)
│   │   │   ├── chunk.py     # Text chunking
│   │   │   └── embed.py     # Embedding generation
│   │   ├── rag/             # RAG components
│   │   │   └── search.py    # Vector search
│   │   ├── storage/         # Database management
│   │   ├── notifier/        # Status notifications
│   │   └── main.py          # Service entry point
│   └── requirements/
└── docker-compose.dev.yml   # Development setup
```

## 🔧 Key Technologies

### Frontend (Client)
- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: Radix UI primitives
- **File Handling**: react-dropzone
- **State Management**: React hooks (useState, useEffect)

### Backend (Server)
- **Runtime**: Node.js with TypeScript
- **Framework**: Express.js
- **WebSocket**: ws library
- **Queue**: amqplib (RabbitMQ client)
- **File Upload**: multer
- **LLM Integration**: @anthropic-ai/sdk, openai

### Processing Service
- **Framework**: FastAPI
- **Document Processing**: Docling 2.24.0
- **Embeddings**: OpenAI text-embedding-3-large
- **Database**: psycopg2-binary, pgvector
- **Queue**: pika (RabbitMQ client)
- **Async Processing**: Threading

### Infrastructure
- **Database**: PostgreSQL with pgvector extension
- **Message Queue**: RabbitMQ
- **Containerization**: Docker & Docker Compose
- **Database Admin**: PgAdmin

## 🗄️ Database Schema

### Tables
```sql
-- Documents metadata
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Text chunks with embeddings
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_text TEXT,
    embedding vector(1536),  -- OpenAI embedding dimension
    page_numbers INTEGER[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity index
CREATE INDEX chunks_embedding_idx 
ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## 🔄 Processing Pipeline

### Document Processing Flow
1. **Upload**: File uploaded to `/api/document/upload`
2. **Queue**: Job queued in RabbitMQ with metadata
3. **Extraction**: Docling extracts text and structure
4. **Chunking**: Text split into optimal chunks (configurable size)
5. **Embedding**: OpenAI generates 1536-dimension vectors
6. **Storage**: Chunks stored in PostgreSQL with metadata
7. **Notification**: WebSocket notifies completion

### Chat Processing Flow
1. **Query**: User message sent to `/api/chat/chat`
2. **Embedding**: Query converted to vector
3. **Search**: Vector similarity search in PostgreSQL
4. **Context**: Top-k results combined with conversation history
5. **Generation**: LLM generates response with context
6. **Response**: Answer returned to client

## 🛠️ Development Patterns

### Error Handling
- **Server**: Express error middleware with structured responses
- **Processing**: Try-catch with retry logic and queue rejection
- **Client**: Error boundaries and user-friendly messages

### Logging
- **Server**: Console logging with structured format
- **Processing**: Python logging with configurable levels
- **Docker**: JSON file logging with rotation

### Configuration
- **Environment Variables**: All secrets and config via .env
- **Docker**: Environment variables in docker-compose
- **TypeScript**: Strong typing for all interfaces

## 🔍 Key Classes and Functions

### Server (Node.js)

#### ChatManager
```typescript
class ChatManager {
  // Handles chat flow orchestration
  async handleMessage(request: ChatRequest): Promise<ChatResponse>
  private async getVectorSearchResults(query: string): Promise<VectorSearchResult[]>
  private buildContext(searchResults: VectorSearchResult[], conversationId: string): string
  private async generateResponse(context: string, userMessage: string): Promise<string>
}
```

#### LLMService
```typescript
class LLMService {
  // Multi-provider LLM integration
  async generateResponse(request: LLMRequest): Promise<LLMResponse>
  setProvider(provider: 'anthropic' | 'openai'): void
}
```

### Processing Service (Python)

#### DocumentProcessor
```python
class DocumentProcessor:
    # Main processing pipeline
    def process_document(self, file_id: str, file_path: str, metadata: Dict = None) -> Dict
```

#### VectorSearch
```python
class VectorSearch:
    # Vector similarity search
    def search(self, query: str, document_id: Optional[int] = None, 
               top_k: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]
    def _generate_embedding(self, text: str) -> List[float]
```

## 🚨 Common Issues and Solutions

### Memory Issues
- **Problem**: Processing service OOM with large documents
- **Solution**: Increase memory limits in docker-compose.yml
- **Monitoring**: `docker stats` to check memory usage

### Queue Connection Issues
- **Problem**: RabbitMQ connection drops during processing
- **Solution**: Implement connection retry logic
- **Monitoring**: Check RabbitMQ management interface

### Database Connection Issues
- **Problem**: PostgreSQL connection pool exhaustion
- **Solution**: Implement connection pooling and proper cleanup
- **Monitoring**: Check database connection count

### WebSocket Issues
- **Problem**: WebSocket connections drop during long processing
- **Solution**: Implement heartbeat and reconnection logic
- **Monitoring**: Check WebSocket connection status

## 🔧 Development Commands

### Local Development
```bash
# Start infrastructure
docker-compose -f docker-compose.dev.yml up postgres rabbitmq pgadmin

# Start API server
cd server && npm run dev

# Start processing service
cd processing-service && python src/main.py

# Start client
cd client && npm run dev
```

### Docker Development
```bash
# Full development environment
npm run dev

# Production build
npm run build && npm start

# View logs
npm run logs
```

### Database Operations
```bash
# Connect to database
docker exec -it pdf_chat_rag-postgres-1 psql -U postgres -d ragdb

# Check vector extension
\dx

# View tables
\dt

# Query chunks
SELECT COUNT(*) FROM chunks;
```

## 📊 Performance Considerations

### Memory Usage
- **Docling Models**: ~6.5GB for OCR models (cached after first run)
- **Processing Service**: 2-7GB depending on document size
- **Database**: Varies with document count and chunk size

### Processing Time
- **Small PDFs** (< 10 pages): 30-60 seconds
- **Medium PDFs** (10-50 pages): 2-5 minutes
- **Large PDFs** (50+ pages): 5-15 minutes

### Optimization Tips
- Use connection pooling for database
- Implement caching for frequent queries
- Batch embedding generation when possible
- Use appropriate chunk sizes for your use case

## 🔒 Security Considerations

### API Keys
- Store in environment variables only
- Never commit to version control
- Use different keys for development/production

### File Upload
- Validate file types and sizes
- Sanitize filenames
- Implement rate limiting

### Database
- Use connection strings with credentials
- Implement proper access controls
- Regular security updates

## 🧪 Testing Strategy

### Unit Tests
- Test individual functions and classes
- Mock external dependencies
- Test error handling paths

### Integration Tests
- Test API endpoints
- Test database operations
- Test queue processing

### End-to-End Tests
- Test complete user workflows
- Test file upload and processing
- Test chat functionality

## 📈 Monitoring and Observability

### Health Checks
- API server health endpoint
- Processing service health endpoint
- Database connectivity checks

### Metrics
- Processing time per document
- Queue depth and processing rate
- Database query performance
- Memory and CPU usage

### Logging
- Structured logging with timestamps
- Error tracking and alerting
- Performance metrics logging

## 🚀 Deployment Considerations

### Production Setup
- Use production-grade database
- Implement proper backup strategies
- Set up monitoring and alerting
- Configure SSL/TLS certificates

### Scaling
- Horizontal scaling of services
- Database read replicas
- Load balancing for API servers
- Queue partitioning for processing

### Maintenance
- Regular database maintenance
- Model updates and migrations
- Security patches and updates
- Performance optimization

## 📚 Learning Opportunities

This project demonstrates:
- **Microservices Architecture**: Service separation and communication
- **RAG Implementation**: Vector search and context retrieval
- **Async Processing**: Message queues and background jobs
- **Real-time Communication**: WebSocket implementation
- **Container Orchestration**: Docker Compose
- **Vector Databases**: PostgreSQL with pgvector
- **LLM Integration**: Multiple provider support
- **TypeScript**: Strong typing and interfaces
- **Python**: FastAPI and async processing
- **React**: Modern hooks and component patterns

## 🤝 Contributing Guidelines

### Code Style
- Follow TypeScript best practices
- Use meaningful variable and function names
- Add proper error handling
- Include type annotations

### Documentation
- Update README for new features
- Add inline code comments
- Document API changes
- Update this agents.md file

### Testing
- Add tests for new features
- Test error scenarios
- Verify integration points
- Test performance implications

