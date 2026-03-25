# PDF-RAG Quick Reference

## 🚀 **Common Commands**

### **Start the System**
```bash
# Start all services
docker compose -f docker-compose.dev.yml up -d

# Start infrastructure only
docker compose -f docker-compose.dev.yml up -d postgres rabbitmq pgadmin

# Start client (separate terminal)
cd client && npm run dev
```

### **Stop the System**
```bash
# Stop all services
docker compose -f docker-compose.dev.yml down

# Stop and remove volumes (fresh start)
docker compose -f docker-compose.dev.yml down -v
```

### **View Logs**
```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker logs pdf-rag-processing-service-1 --tail 50
docker logs pdf-rag-server-1 --tail 50
```

### **Check Service Status**
```bash
# Container status
docker compose -f docker-compose.dev.yml ps

# Service health
curl http://localhost:3000/health
curl http://localhost:8000/health
```

---

## 🔧 **Debugging Commands**

### **Environment Variables**
```bash
# Check if variables are set
docker exec pdf-rag-server-1 env | grep INTERNAL_API_KEY
docker exec pdf-rag-processing-service-1 env | grep OPENAI_API_KEY

# Check Docker Compose config
docker compose -f docker-compose.dev.yml config | grep -A 5 -B 5 INTERNAL_API_KEY
```

### **Database Operations**
```bash
# Connect to database
docker exec -it pdf-rag-postgres-1 psql -U postgres -d ragdb

# Check tables
docker exec pdf-rag-postgres-1 psql -U postgres -d ragdb -c "\dt"

# Check extensions
docker exec pdf-rag-postgres-1 psql -U postgres -d ragdb -c "\dx"

# View recent documents
docker exec pdf-rag-postgres-1 psql -U postgres -d ragdb -c "SELECT * FROM documents ORDER BY created_at DESC LIMIT 5;"
```

### **Network Testing**
```bash
# Test service connectivity
docker exec pdf-rag-processing-service-1 ping postgres
docker exec pdf-rag-processing-service-1 ping rabbitmq

# Check RabbitMQ
docker exec pdf-rag-rabbitmq-1 rabbitmq-diagnostics check_port_connectivity
```

---

## 🌐 **Service URLs**

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3500 | Upload documents, chat interface |
| API Server | http://localhost:3000 | REST API, WebSocket |
| Processing Service | http://localhost:8000 | Document processing API |
| PgAdmin | http://localhost:5050 | Database administration |
| RabbitMQ Management | http://localhost:15672 | Message queue management |

**Default Credentials:**
- PgAdmin: `admin@example.com` / `adminpassword`
- RabbitMQ: `guest` / `guest`

---

## 📁 **Important Files**

### **Configuration**
- `docker-compose.dev.yml` - Docker services configuration
- `.env` - Environment variables (root directory)
- `init.sql` - Database schema initialization

### **Key Components**
- `server/src/api/routes/` - API endpoints
- `server/src/services/` - Business logic
- `processing-service/src/process_pipeline/` - Document processing
- `processing-service/src/rag/` - Vector search
- `client/src/components/` - Frontend components

---

## 🔄 **Development Workflow**

### **1. Make Changes**
```bash
# Edit code files
# Changes are automatically reflected in containers (volume mounts)
```

### **2. Test Changes**
```bash
# Check logs
docker logs pdf-rag-processing-service-1 --tail 20

# Test API endpoints
curl http://localhost:3000/api/health
```

### **3. Restart Services (if needed)**
```bash
# Restart specific service
docker compose -f docker-compose.dev.yml restart processing-service

# Rebuild and restart
docker compose -f docker-compose.dev.yml up --build processing-service
```

---

## 🚨 **Emergency Fixes**

### **Reset Everything**
```bash
# Stop all services and remove volumes
docker compose -f docker-compose.dev.yml down -v

# Remove all containers and images
docker system prune -a

# Start fresh
docker compose -f docker-compose.dev.yml up -d
```

### **Fix Port Conflicts**
```bash
# Kill process using port 3500
lsof -ti:3500 | xargs kill -9

# Or use different port
cd client && npm run dev -- -p 3501
```

### **Reset Database**
```bash
# Remove database volume
docker volume rm pdf-rag_postgres_data

# Restart postgres
docker compose -f docker-compose.dev.yml up -d postgres
```

---

## 📊 **Monitoring**

### **Resource Usage**
```bash
# Container resource usage
docker stats

# Disk usage
docker system df
```

### **Log Analysis**
```bash
# Search logs for errors
docker logs pdf-rag-processing-service-1 2>&1 | grep -i error

# Follow logs in real-time
docker logs -f pdf-rag-processing-service-1
```

---

## 🔐 **Security Notes**

- Never commit `.env` files to version control
- Use strong `INTERNAL_API_KEY` in production
- Rotate API keys regularly
- Monitor API usage and costs

---

**Last Updated:** October 24, 2025



