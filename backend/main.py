# backend/main.py

from fastapi import FastAPI
from pydantic import BaseModel
import docker

# Import the SandboxManager we just wrote
from sandbox import SandboxManager

app = FastAPI(title="ComputeAgent API")

# Initialize the Sandbox Manager once when the server starts
sandbox = SandboxManager()

# 1. Define the Expected Request Body
# This tells FastAPI: "Expect a JSON object with a single string field named 'code'"
class CodeExecutionRequest(BaseModel):
    code: str

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "message": "ComputeAgent backend is running",
        "docker_connected": True
    }

# 2. Create the Execution Endpoint
@app.post("/api/execute")
def execute_python_code(request: CodeExecutionRequest):
    """
    Receives Python code, sends it to the Docker sandbox, and returns the result.
    """
    # We access the string inside the request using `request.code`
    result = sandbox.execute_code(request.code)
    
    return result