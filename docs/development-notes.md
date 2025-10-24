# Development Notes - PDF-RAG Project

## 🐛 **Major Debugging Session - October 24, 2025**

### **Session Summary**
Resolved critical issues preventing the PDF-RAG system from processing documents end-to-end.

---

## 🔍 **Issues Discovered & Resolved**

### **1. Processing Service Silent Failures**

**Problem:** Processing service was failing to start with empty error messages, making debugging extremely difficult.

**Root Cause:** Missing `__len__` method in the `OpenAITokenizerWrapper` class caused a `NotImplementedError` in the transformers library.

**Solution:**
```python
# Added to processing-service/src/utils/tokenizer.py
def __len__(self) -> int:
    """Return the vocabulary size."""
    return self.vocab_size
```

**Lesson Learned:** When using custom tokenizer wrappers with HuggingFace transformers, ensure all required methods are implemented, especially `__len__`.

---

### **2. Environment Variable Loading Issues**

**Problem:** The Node.js server couldn't load environment variables from the root `.env` file when running locally.

**Root Cause:** The `dotenv.config()` was looking for `.env` in the wrong directory.

**Attempted Solutions:**
- Added `dotenv.config({ path: path.resolve(__dirname, '../../../.env') })` 
- User reverted changes, indicating preference for Docker-based development

**Lesson Learned:** The project is designed for Docker-first development. Local development requires careful path configuration for environment variables.

---

### **3. Service-to-Service Authentication**

**Problem:** Processing service couldn't send notifications to the server due to 401 Unauthorized errors.

**Root Cause:** Missing `INTERNAL_API_KEY` environment variable in both services.

**Solution:**
1. Added `INTERNAL_API_KEY` to both server and processing service environments in `docker-compose.dev.yml`
2. Used environment variable substitution: `${INTERNAL_API_KEY:-development_key}`
3. Updated README.md to document the new environment variable
4. Restarted all containers to pick up the new environment variables

**Key Insight:** Environment variables are set at container creation time. Changes require container recreation, not just restart.

---

### **4. Docker Container Startup Order**

**Problem:** Processing service failed to connect to database due to hostname resolution issues.

**Root Cause:** Processing service was starting before the database container was fully ready.

**Solution:** Start infrastructure services first, then application services:
```bash
docker compose -f docker-compose.dev.yml up -d postgres rabbitmq pgadmin
# Wait for health checks
docker compose -f docker-compose.dev.yml up processing-service server
```

**Lesson Learned:** Use Docker Compose health checks and proper service dependencies to ensure startup order.

---

## 🛠️ **Debugging Techniques That Worked**

### **1. Enhanced Error Logging**
Added detailed error handling and logging to identify silent failures:

```python
# In DocumentProcessor.__init__
try:
    self.embedder = TextEmbedder(db_manager)
    print("✓ Text embedder initialized")
except Exception as e:
    print(f"✗ Failed to initialize DocumentProcessor: {e}")
    import traceback
    traceback.print_exc()
    raise
```

### **2. Step-by-Step Service Testing**
Instead of starting all services at once, tested each service individually:

1. Infrastructure (PostgreSQL, RabbitMQ)
2. Processing service
3. Server
4. Client

### **3. Environment Variable Verification**
```bash
# Check if Docker Compose sees the variables
docker compose -f docker-compose.dev.yml config | grep INTERNAL_API_KEY

# Verify variables are in containers
docker exec pdf-rag-server-1 env | grep INTERNAL_API_KEY
```

---

## 📋 **Configuration Changes Made**

### **docker-compose.dev.yml**
```yaml
# Added to both server and processing-service environments
- INTERNAL_API_KEY=${INTERNAL_API_KEY:-development_key}
```

### **processing-service/src/utils/tokenizer.py**
```python
def __len__(self) -> int:
    """Return the vocabulary size."""
    return self.vocab_size
```

### **processing-service/src/process_pipeline/processor.py**
```python
# Added detailed error handling and logging
try:
    self.embedder = TextEmbedder(db_manager)
    print("✓ Text embedder initialized")
except Exception as e:
    print(f"✗ Failed to initialize DocumentProcessor: {e}")
    import traceback
    traceback.print_exc()
    raise
```

### **processing-service/src/process_pipeline/embed.py**
```python
# Added better error handling for OpenAI client initialization
try:
    logger.info(f"Initializing OpenAI client with API key: {api_key[:10]}...")
    self.client = OpenAI(api_key=api_key)
    logger.info("Text embedder initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize TextEmbedder: {e}", exc_info=True)
    raise
```

---

## 🎯 **Key Takeaways**

### **1. Docker-First Development**
This project is designed for containerized development. Local development requires significant configuration adjustments.

### **2. Environment Variable Management**
- Use environment variable substitution in Docker Compose: `${VAR:-default}`
- Environment variables are set at container creation time
- Always restart containers after environment changes
- Document all required environment variables

### **3. Service Dependencies**
- Use health checks to ensure proper startup order
- Start infrastructure services before application services
- Test services individually before integration testing

### **4. Error Handling**
- Add detailed logging to identify silent failures
- Use try-catch blocks with proper error propagation
- Print stack traces for debugging

### **5. Third-Party Library Compatibility**
- When wrapping third-party libraries, ensure all required methods are implemented
- Test custom wrappers thoroughly with the target library
- Check library documentation for required interface methods

---

## 🚀 **Next Steps**

1. **Implement Chat Functionality** - The core RAG system is working, now implement the chat interface
2. **Add Error Recovery** - Implement retry logic for failed document processing
3. **Performance Optimization** - Optimize embedding generation and database queries
4. **Monitoring** - Add health checks and monitoring endpoints
5. **Testing** - Add comprehensive test suite for all components

---

## 📚 **Resources Used**

- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [HuggingFace Transformers Tokenizer](https://huggingface.co/docs/transformers/main/en/main_classes/tokenizer)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [PostgreSQL pgvector Extension](https://github.com/pgvector/pgvector)

---

**Session Date:** October 24, 2025  
**Duration:** ~2 hours  
**Issues Resolved:** 4 major issues  
**Status:** ✅ System fully operational
