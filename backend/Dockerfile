# backend/Dockerfile
FROM python:3.11-slim

# Install uv directly from the official astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy the project files
COPY . .

# Use uv to install dependencies instantly
RUN uv sync

# Expose the API port
EXPOSE 8000

# Start the FastAPI server
CMD ["uv", "run", "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]