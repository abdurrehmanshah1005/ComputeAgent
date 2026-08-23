
# ComputeAgent

An asynchronous, AI-powered data analysis platform built with a containerized microservices architecture.

## Architecture
- **Frontend:** React, TypeScript, Vite
- **Backend API:** FastAPI (Python)
- **Message Broker:** Redis
- **Background Task Worker:** Celery
- **Database:** PostgreSQL
- **Execution Environment:** Isolated Docker Sandbox with POSIX-secured Named Volumes

## How to Run
1. Ensure Docker Desktop is running.
2. Build and start the infrastructure:
   ```bash
   docker-compose up -d --build