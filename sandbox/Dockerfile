# 1. Use a lightweight official Python image
FROM python:3.11-slim

# 2. Create a non-root user for security
RUN useradd -m -s /bin/bash sandboxuser

# 3. Set the working directory
WORKDIR /workspace

# 4. Install basic data science packages
RUN pip install --no-cache-dir numpy pandas matplotlib sympy

# 5. Switch to the non-root user
USER sandboxuser

# 6. Default command
CMD ["python3"]