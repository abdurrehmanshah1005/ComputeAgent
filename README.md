# ComputeAgent 🧠📊

An asynchronous, AI-powered data analysis platform built with a containerized microservices architecture. ComputeAgent allows users to upload datasets and natural language prompts, securely executing AI-generated Python code in isolated sandboxes to produce data visualizations and insights.

![Generated Analysis Dashboard](assets/demo-dashboard.jpg)
*Example output: A multi-panel sales data dashboard generated dynamically in a secure, ephemeral container.*

## 🏗️ System Architecture

This platform is designed around a distributed, event-driven architecture to ensure high performance and strict security boundaries.

* **Frontend:** React, TypeScript, and Vite, served via an **Nginx** web server.
* **Backend API:** **FastAPI** handling RESTful routing and artifact management.
* **Message Broker:** **Redis** for asynchronous task queuing.
* **Background Workers:** **Celery** workers that distribute heavy AI processing away from the main web thread.
* **Database:** **PostgreSQL** for persistent execution tracking and state management.
* **Execution Environment:** Isolated **Docker-in-Docker** sandboxing. The worker daemon dynamically spins up restricted, unprivileged Linux containers to execute generated code.

## 🔒 Security Features

* **Socket Isolation:** The web container is completely isolated from the host Docker socket.
* **Privilege Dropping:** Code execution runs as a restricted, unprivileged user (UID 1000) inside the sandbox.
* **POSIX Permissions:** Shared named volumes are strictly locked down using precise process ownership (`chown`) and restricted directory permissions (`chmod 755`) to prevent privilege escalation.

## 🚀 How to Run Locally

1. Ensure **Docker Desktop** (or the Docker daemon) is running.
2. Clone the repository and navigate into the root directory:

   ```bash
   git clone https://github.com/yourusername/ComputeAgent.git
   cd ComputeAgent
   ```

3. Build and launch the entire microservices stack:

   ```bash
   docker-compose up -d --build
   ```

4. Access the platform:

   - **Web UI:** `http://localhost:5173`
   - **API Documentation:** `http://localhost:8000/docs`

## 🛑 Shutting Down

To gracefully shut down the infrastructure and free up system resources, run:

```bash
docker-compose down
```

## ⚙️ CI/CD Pipeline

The repository includes a fully configured **GitHub Actions** workflow. Upon pushing to the `main` branch, the pipeline automatically builds and publishes the production-ready Docker images (Frontend, Backend, and Worker) to the GitHub Container Registry (GHCR), ensuring the platform is immediately ready for cloud VM deployment.