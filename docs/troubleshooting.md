# PDF-RAG Troubleshooting Guide

## 🚨 Common Issues and Solutions

This document contains solutions to common issues encountered during development and deployment of the PDF-RAG system.

---

## 🔧 **Processing Service Issues**

### **Issue: Processing Service Fails to Start with Silent Errors**

**Symptoms:**
- Processing service shows "Attempt X failed:" with empty error messages
- Service keeps retrying and eventually exits
- No clear error information in logs

**Root Causes & Solutions:**

#### **1. Missing `__len__` Method in Tokenizer**
```python
# Error: NotImplementedError in transformers library
# File: processing-service/src/utils/tokenizer.py

# Solution: Add missing __len__ method
def __len__(self) -> int:
    """Return the vocabulary size."""
    return self.vocab_size
```

#### **2. Database Connection Issues**
```bash
# Error: could not translate host name "postgres" to address
# Solution: Ensure database container is running first
docker compose -f docker-compose.dev.yml up -d postgres rabbitmq pgadmin
# Then start processing service
docker compose -f docker-compose.dev.yml up processing-service
```

#### **3. OpenAI API Quota Exceeded**
```bash
# Error: 429 - You exceeded your current quota
# Solution: Add credit to OpenAI account or check API key
# Verify API key is working:
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

---

## 🔐 **Authentication Issues**

### **Issue: 401 Unauthorized in Service-to-Service Communication**

**Symptoms:**
- Processing service fails to send notifications to server
- Error: `Failed to send notification: 401 - {"error":"Unauthorized"}`

**Root Cause:**
Missing or mismatched `INTERNAL_API_KEY` environment variable between services.

**Solution:**
1. **Add to `.env` file:**
   ```env
   INTERNAL_API_KEY=your_secure_internal_key_here
   ```

2. **Update docker-compose.dev.yml:**
   ```yaml
   # Server environment
   environment:
     - INTERNAL_API_KEY=${INTERNAL_API_KEY:-development_key}
   
   # Processing service environment  
   environment:
     - INTERNAL_API_KEY=${INTERNAL_API_KEY:-development_key}
   ```

3. **Restart containers:**
   ```bash
   docker compose -f docker-compose.dev.yml down
   docker compose -f docker-compose.dev.yml up -d
   ```

4. **Verify environment variables:**
   ```bash
   docker exec pdf-rag-server-1 env | grep INTERNAL_API_KEY
   docker exec pdf-rag-processing-service-1 env | grep INTERNAL_API_KEY
   ```

---

## 🌐 **Environment Variable Issues**

### **Issue: Environment Variables Not Loading**

**Symptoms:**
- Services can't find required environment variables
- API keys not working despite being set in `.env`

**Solutions:**

#### **1. Check `.env` File Location**
```bash
# .env file must be in root directory (same level as package.json)
ls -la | grep .env
```

#### **2. Verify Docker Compose is Reading Variables**
```bash
# Check if Docker Compose sees the variables
docker compose -f docker-compose.dev.yml config | grep -A 5 -B 5 YOUR_VARIABLE
```

#### **3. Force Container Recreation**
```bash
# Environment variables are set at container creation time
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d
```

#### **4. Check Container Environment**
```bash
# Verify variables are actually in the container
docker exec pdf-rag-server-1 env | grep YOUR_VARIABLE
```

---

## 🐳 **Docker Issues**

### **Issue: Port Already in Use**

**Symptoms:**
```
Error: listen EADDRINUSE: address already in use :::3500
```

**Solution:**
```bash
# Find and kill process using the port
lsof -ti:3500 | xargs kill -9

# Or use a different port
cd client && npm run dev -- -p 3501
```

### **Issue: Container Networking Problems**

**Symptoms:**
- Services can't communicate with each other
- Hostname resolution failures

**Solution:**
```bash
# Ensure all services are in the same Docker network
docker compose -f docker-compose.dev.yml ps

# Check network connectivity
docker exec pdf-rag-processing-service-1 ping postgres
docker exec pdf-rag-processing-service-1 ping rabbitmq
```

---

## 📊 **Database Issues**

### **Issue: Database Tables Don't Exist**

**Symptoms:**
- Processing service fails with database errors
- Tables missing despite init.sql

**Solution:**
```bash
# Check if tables exist
docker exec pdf-rag-postgres-1 psql -U postgres -d ragdb -c "\dt"

# Check if vector extension is installed
docker exec pdf-rag-postgres-1 psql -U postgres -d ragdb -c "\dx"

# If missing, restart with fresh volumes
docker compose -f docker-compose.dev.yml down
docker volume rm pdf-rag_postgres_data
docker compose -f docker-compose.dev.yml up -d postgres
```

---

## 🔍 **Debugging Techniques**

### **1. Enable Verbose Logging**
```python
# Add to processing service
import logging
logging.basicConfig(level=logging.DEBUG)
```

### **2. Check Service Health**
```bash
# Check all services status
docker compose -f docker-compose.dev.yml ps

# Check individual service logs
docker logs pdf-rag-processing-service-1 --tail 50
docker logs pdf-rag-server-1 --tail 50
```

### **3. Test API Endpoints**
```bash
# Test server health
curl http://localhost:3000/health

# Test processing service
curl http://localhost:8000/health
```

### **4. Database Debugging**
```bash
# Connect to database
docker exec -it pdf-rag-postgres-1 psql -U postgres -d ragdb

# Check recent documents
SELECT * FROM documents ORDER BY created_at DESC LIMIT 5;

# Check chunks
SELECT COUNT(*) FROM chunks;
```

---

## 🚀 **Performance Issues**

### **Issue: Slow Document Processing**

**Solutions:**
1. **Increase memory limits:**
   ```yaml
   # In docker-compose.dev.yml
   deploy:
     resources:
       limits:
         memory: 7G
   ```

2. **Optimize chunk size:**
   ```python
   # In processing-service/src/process_pipeline/chunk.py
   self.chunker = HybridChunker(
       max_tokens=4096,  # Reduce from 8191
   )
   ```

3. **Batch embedding requests:**
   ```python
   # Process multiple chunks in single API call
   # (Implementation depends on OpenAI API limits)
   ```

---

## 📝 **Development Workflow**

### **Best Practices:**

1. **Always check logs first:**
   ```bash
   docker logs pdf-rag-processing-service-1 --tail 20
   ```

2. **Test services individually:**
   ```bash
   # Start infrastructure first
   docker compose -f docker-compose.dev.yml up -d postgres rabbitmq pgadmin
   
   # Then start services
   docker compose -f docker-compose.dev.yml up server processing-service
   ```

3. **Use environment variables properly:**
   ```bash
   # Never hardcode secrets
   # Use .env file in root directory
   # Restart containers after env changes
   ```

4. **Monitor resource usage:**
   ```bash
   docker stats
   ```

---

## 🔧 **Quick Fixes Checklist**

When something breaks, check these in order:

- [ ] Are all containers running? (`docker compose ps`)
- [ ] Are environment variables set? (`docker exec container env | grep VAR`)
- [ ] Are services healthy? (`docker logs container --tail 10`)
- [ ] Is the database accessible? (`docker exec postgres psql -U postgres -d ragdb -c "\dt"`)
- [ ] Are API keys valid? (Test with curl)
- [ ] Is the network working? (`docker exec container ping other-service`)

---

## 📚 **Additional Resources**

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL with pgvector](https://github.com/pgvector/pgvector)
- [RabbitMQ Management](https://www.rabbitmq.com/management.html)
- [OpenAI API Documentation](https://platform.openai.com/docs)

---

**Last Updated:** October 24, 2025  
**Version:** 1.0
