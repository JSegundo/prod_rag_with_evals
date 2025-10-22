# PDF-RAG: Intelligent Document Chat System

A sophisticated Retrieval-Augmented Generation (RAG) system that allows users to upload PDF documents and chat with them using AI. Built with a microservices architecture using Node.js, Python, and modern web technologies.

## 🏗️ Architecture Overview

This project implements a distributed RAG system with three main components:

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

### **Frontend (Next.js Client)**
- **Port**: 3500
- **Technology**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Features**: PDF upload interface, real-time processing status, chat interface
- **Components**: PDF dropzone, processing status tracker, chat UI

### **API Server (Node.js)**
- **Port**: 3000
- **Technology**: Express.js, TypeScript, WebSocket
- **Responsibilities**: 
  - File upload handling
  - Chat orchestration
  - WebSocket communication
  - LLM integration (Anthropic/OpenAI)
  - Queue management

### **Processing Service (Python)**
- **Port**: 8000
- **Technology**: FastAPI, Docling, OpenAI Embeddings
- **Responsibilities**:
  - PDF text extraction using Docling
  - Text chunking and preprocessing
  - Vector embedding generation
  - Vector search operations
  - Database management

### **Infrastructure**
- **PostgreSQL with pgvector**: Vector database for embeddings
- **RabbitMQ**: Message queue for asynchronous processing
- **Docker**: Containerized deployment
- **PgAdmin**: Database administration interface

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.9+ (for local development)
- Virtual environment support (venv or conda)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pdf-RAG
   ```

2. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # OpenAI API Key (required for embeddings)
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Anthropic API Key (for chat responses)
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   
   # Database Configuration
   DATABASE_URL=postgres://postgres:yourpassword@postgres:5432/ragdb
   
   # RabbitMQ Configuration
   RABBITMQ_URL=amqp://rabbitmq:5672
   
   # Processing Service Configuration
   PROCESSING_SERVICE_URL=http://localhost:8000
   UPLOADS_DIR=/app/uploads
   ```

3. **Start the system**
   ```bash
   # Development mode with hot reload
   npm run dev
   
   # Or production mode
   npm start
   ```

4. **Access the application**
   - **Frontend**: http://localhost:3500
   - **API Server**: http://localhost:3000
   - **Processing Service**: http://localhost:8000
   - **PgAdmin**: http://localhost:5050 (admin@example.com / adminpassword)
   - **RabbitMQ Management**: http://localhost:15672 (guest / guest)

### Virtual Environment Best Practices

When working with the Python processing service locally:

```bash
# Always activate the virtual environment before working
cd processing-service
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install new dependencies
pip install package_name
pip freeze > requirements/base.txt  # Update requirements file

# Deactivate when done
deactivate
```

**Important Notes:**
- The virtual environment is excluded from version control (see `.gitignore`)
- Always use the virtual environment for local development
- Update `requirements.txt` files when adding new dependencies
- Docker containers use their own isolated environments

## 📋 Detailed Setup Instructions

### Development Setup

1. **Start infrastructure services**
   ```bash
   docker-compose -f docker-compose.dev.yml up postgres rabbitmq pgadmin
   ```

2. **Install and run the API server**
   ```bash
   cd server
   npm install
   npm run dev
   ```

3. **Install and run the processing service**
   ```bash
   cd processing-service
   
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements/base.txt
   pip install -r requirements/heavy.txt
   
   # Run the service
   python src/main.py
   ```

4. **Install and run the client**
   ```bash
   cd client
   npm install
   npm run dev
   ```

### Production Setup

1. **Build and start all services**
   ```bash
   docker-compose up --build
   ```

2. **Monitor logs**
   ```bash
   docker-compose logs -f
   ```

## 🔄 How It Works

### Document Processing Flow

1. **Upload**: User uploads PDF through the web interface
2. **Queue**: File is queued for processing via RabbitMQ
3. **Extraction**: Docling extracts text and structure from PDF
4. **Chunking**: Text is split into optimal chunks for embedding
5. **Embedding**: OpenAI generates vector embeddings for each chunk
6. **Storage**: Chunks and embeddings are stored in PostgreSQL with pgvector
7. **Notification**: WebSocket notifies frontend of completion

### Chat Flow

1. **Query**: User sends a message through the chat interface
2. **Vector Search**: Query is embedded and searched against stored chunks
3. **Context Building**: Relevant chunks are retrieved and combined with conversation history
4. **LLM Generation**: Anthropic/OpenAI generates response using the context
5. **Response**: Answer is streamed back to the user

## 🛠️ API Endpoints

### Document Management
- `POST /api/document/upload` - Upload PDF file
- `GET /api/document/status/:fileId` - Get processing status

### Chat
- `POST /api/chat/chat` - Send chat message
- `GET /api/chat/history/:conversationId` - Get conversation history

### Processing Service
- `POST /api/search` - Vector search
- `GET /api/health` - Health check

## 🗄️ Database Schema

The database schema is defined in `init.sql` and includes:

- **documents**: Stores document metadata
- **chunks**: Stores text chunks with vector embeddings (1536 dimensions)
- **vector extension**: PostgreSQL pgvector for similarity search

See `init.sql` for the complete schema definition.

## 🔧 Configuration

### Docker Compose Services

- **postgres**: PostgreSQL with pgvector extension
- **rabbitmq**: Message queue with management interface
- **pgadmin**: Database administration
- **server**: Node.js API server
- **processing-service**: Python processing service

### Resource Limits

The processing service is configured with:
- Memory limit: 7GB
- Memory reservation: 2GB
- Restart policy: on-failure

## 🐛 Troubleshooting

**Common Issues:**
- **Processing stuck**: Check memory usage with `docker stats`, restart with `docker-compose restart processing-service`
- **Large documents fail**: Increase memory limits in docker-compose.yml
- **Database issues**: Verify PostgreSQL is running with `docker-compose ps`
- **OCR models**: First run downloads ~6.5GB, ensure sufficient disk space

## 📊 Monitoring

**Health Checks:**
- API Server: `GET http://localhost:3000/health`
- Processing Service: `GET http://localhost:8000/api/health`

**Logs:**
```bash
docker-compose logs -f  # All services
docker-compose logs -f processing-service  # Specific service
```

## 🔒 Security Considerations

- API keys are stored in environment variables
- File uploads are validated and size-limited
- Database connections use connection pooling
- CORS is configured for development


## 📊 Architecture Analysis & Recommendations

For detailed analysis of the current architecture, identified issues, and improvement recommendations, see [recommendations.md](./recommendations.md). This document includes:

- Current architecture strengths and weaknesses
- Immediate fixes for production readiness
- Medium-term improvements for scalability
- Long-term vision for advanced AI capabilities
- Performance optimization strategies
- Future implementation ideas for agentic patterns


