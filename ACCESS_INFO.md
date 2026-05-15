/# 🔗 How to Access T1D Companion

## Local Development URLs

### Backend API (FastAPI)
```
http://localhost:8000
```

**Endpoints:**
- API Docs (Swagger): `http://localhost:8000/docs`
- API Docs (ReDoc): `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

### Frontend (Vite/React)
```
http://localhost:3000
```

**Pages:**
- Dashboard: `http://localhost:3000/dashboard`
- Glucose: `http://localhost:3000/glucose`
- Events: `http://localhost:3000/events`
- Patterns: `http://localhost:3000/patterns`
- Chat: `http://localhost:3000/chat`
- Login: `http://localhost:3000/login`
- Settings: `http://localhost:3000/settings`

### Services
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **Celery Worker**: Background tasks
- **Celery Beat**: Scheduled tasks

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
cd /Users/russellbatchelor/projects/T1D
docker-compose up --build
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd /Users/russellbatchelor/projects/T1D
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /Users/russellbatchelor/projects/T1D/frontend
npm run dev
```

**Terminal 3 - Celery Worker:**
```bash
cd /Users/russellbatchelor/projects/T1D
celery -A app.services.sync_service.celery_app worker --loglevel=info
```

**Terminal 4 - Celery Beat:**
```bash
cd /Users/russellbatchelor/projects/T1D
celery -A app.services.sync_service.celery_app beat --loglevel=info
```

---

## 🔑 Test Credentials

### Demo Account
```
Email:    demo@t1d.com
Password: demo123
```

### Register New User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@t1d.com",
    "password": "demo123"
  }'
```

---

## 📱 Mobile Access

### On Same Network
If accessing from another device on the same network:

1. Find your local IP:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "
   
   # Windows
   ipconfig
   ```

2. Access from mobile:
   - Frontend: `http://<YOUR_LOCAL_IP>:3000`
   - Backend: `http://<YOUR_LOCAL_IP>:8000`

### Ngrok (Public URL)
```bash
# Install ngrok
npm install -g ngrok

# Expose frontend
ngrok http 3000

# Expose backend
ngrok http 8000
```

---

## 🔧 Environment Configuration

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://t1d_user:password@localhost:5432/t1d_db

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256

# LLM APIs (Optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
OPENROUTER_API_KEY=sk-...
```

### Frontend (.env)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## 🐳 Docker Services

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up --build -d

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

**Services:**
- `t1d-backend` - FastAPI (port 8000)
- `t1d-frontend` - Vite/React (port 3000)
- `t1d-db` - PostgreSQL (port 5432)
- `t1d-redis` - Redis (port 6379)
- `t1d-worker` - Celery worker
- `t1d-beat` - Celery beat scheduler

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -ti:3000

# Kill process
kill -9 <PID>

# Or change port
cd frontend && npm run dev -- --port 3001
```

### Database Connection Failed
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Start PostgreSQL (macOS)
brew services start postgresql

# Reset database
cd /Users/russellbatchelor/projects/T1D
alembic upgrade head
```

### Frontend Build Errors
```bash
# Clean and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Backend Import Errors
```bash
# Install dependencies
cd /Users/russellbatchelor/projects/T1D
pip install -e .

# Run migrations
alembic upgrade head
```

---

## 🌐 Network Troubleshooting

### CORS Issues
If frontend can't access backend:
```python
# In app/main.py, update CORS origins
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]
```

### WebSocket Issues
```bash
# Check WebSocket endpoint
ws://localhost:8000/ws

# Test with wscat
npm install -g wscat
wscat -c ws://localhost:8000/ws
```

---

## 📄 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Key Endpoints:**
```
GET   /api/v1/health              - Health check
POST  /api/v1/auth/login          - User login
GET   /api/v1/glucose/recent      - Recent readings
POST  /api/v1/events              - Create event
POST  /api/v1/chat                - Chat with AI
GET   /api/v1/patterns/analyze    - Analyze patterns
```

---

## 🎯 Quick Test

```bash
# Test backend health
curl http://localhost:8000/health

# Test login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@t1d.com","password":"demo123"}'

# Open frontend in browser
open http://localhost:3000
```

---

## 🚀 Production Deployment

### For Public Access

**Using Ngrok:**
```bash
ngrok http 3000
# Share the https://*.ngrok.io URL
```

**Using Cloud Services:**
- **Render**: Free tier available
- **Fly.io**: Global edge deployment
- **Railway**: Easy deployment
- **AWS ECS/Fargate**: Production-grade
- **DigitalOcean App Platform**: Simple scaling

### Domain Setup
1. Point domain to server IP
2. Configure reverse proxy (Nginx)
3. Enable HTTPS (Let's Encrypt)
4. Set environment variables
5. Configure database backups

---

## 📞 Support

### Check Logs
```bash
# Backend logs
cd /Users/russellbatchelor/projects/T1D
docker-compose logs -f backend

# Frontend logs
cd frontend && npm run build 2>&1 | tail -20

# Celery logs
docker-compose logs -f worker
```

### Common Issues
- [Frontend won't start](https://vitejs.dev/guide/troubleshooting.html)
- [Backend import errors](https://fastapi.tiangolo.com/troubleshooting/)
- [Database connection](https://www.postgresql.org/docs/current/runtime-config.html)

---

## 🔐 Security Checklist

- [ ] Change default passwords
- [ ] Use strong JWT secret
- [ ] Enable HTTPS in production
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable audit logging
- [ ] Regular backups
- [ ] Update dependencies
- [ ] Use environment variables (not hardcoded secrets)
- [ ] Database user has minimal privileges

---

## 🎉 You're Ready!

**Local URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Demo Login:**
- Email: demo@t1d.com
- Password: demo123

**Need Help?**
Check the logs or visit the project README for more details.

*Happy coding! 🚀*