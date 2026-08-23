# backend/main.py

from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session


import shutil
import os
import uuid

from pydantic import BaseModel
from dotenv import load_dotenv

import re
from pathlib import Path
from sqlalchemy import desc

# Import our database dependencies
from database import get_db, engine
import models
from worker import run_analysis_job

# Load the .env file so the API key is available
load_dotenv()

from sandbox import SandboxManager
from agent import CodeAgent

app = FastAPI(title="ComputeAgent API")

# backend/main.py
from database import engine, Base
import models

# Create the tables in the database
models.Base.metadata.create_all(bind=engine)

def secure_filename(filename: str) -> str:
    """
    Strips directory paths and removes dangerous characters.
    '../../../etc/passwd' becomes 'passwd'
    """
    # 1. Extract just the file name, dropping any folder paths
    base_name = Path(filename).name 
    # 2. Replace any character that isn't a letter, number, dot, dash, or underscore with an underscore
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
    
    # Fallback in case the name was entirely stripped
    return safe_name if safe_name else "uploaded_file"

sandbox = SandboxManager()
agent = CodeAgent()

# The user now sends a natural language prompt, not raw code
class AgentRequest(BaseModel):
    prompt: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/chat")
def ask_agent(request: AgentRequest):
    """
    1. Sends the user's prompt to Gemini.
    2. Gemini generates Python code.
    3. The sandbox executes the code.
    4. Returns both the code and the execution result.
    """
    # Step 1: Generate the code (Costs 1 API Call)
    try:
        generated_code = agent.generate_python_code(request.prompt)
    except Exception as e:
        return {"status": "api_error", "message": str(e)}

    # Step 2: Execute the code safely in Docker (Costs 0 API Calls)
    execution_result = sandbox.execute_code(generated_code)

    # Step 3: Return everything to the user
    return {
        "prompt": request.prompt,
        "generated_code": generated_code,
        "execution": execution_result
    }

@app.post("/api/analyze")
def analyze_file(
    prompt: str = Form(...), 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    execution_id = str(uuid.uuid4())
    workspace_dir = f"workspaces/{execution_id}"
    os.makedirs(workspace_dir, exist_ok=True)
    # SECURITY/PERMISSION FIX: Grant the restricted sandbox user write access
    os.chmod(workspace_dir, 0o777)

    safe_filename = secure_filename(file.filename)
    file_path = os.path.join(workspace_dir, safe_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Create a "pending" database record instantly
    db_execution = models.Execution(
        id=execution_id,
        prompt=prompt,
        generated_code="Pending generation...",
        status="queued",  # Note the new status
        output_logs=""
    )
    db.add(db_execution)
    db.commit()

    # 2. Hand the heavy lifting to the background worker via Redis
    run_analysis_job.delay(execution_id, prompt, safe_filename)

    # 3. Return immediately to the user (takes ~50 milliseconds)
    return {
        "execution_id": execution_id,
        "status": "queued",
        "message": "Job submitted successfully. Poll /api/executions to see the result."
    }

@app.get("/api/artifacts/{execution_id}/{filename}")
def download_artifact(execution_id: str, filename: str):
    """
    Safely serves generated files back to the user, preventing path traversal.
    """
    # Ensure execution_id only contains safe characters (alphanumeric and dashes for UUIDs)
    if not re.match(r'^[a-f0-9-]+$', execution_id):
        return {"error": "Invalid execution ID"}, 400

    # Resolve the absolute path to the intended workspace directory
    workspace_dir = os.path.abspath(os.path.join("workspaces", execution_id))
    
    # Sanitize the requested filename and resolve its absolute path
    safe_filename = secure_filename(filename)
    requested_file_path = os.path.abspath(os.path.join(workspace_dir, safe_filename))

    # SECURITY FIX: Ensure the requested file path starts strictly with the workspace path.
    # This prevents an attacker from downloading files outside their specific sandbox.
    if not requested_file_path.startswith(workspace_dir):
        return {"error": "Access denied"}, 403

    if os.path.exists(requested_file_path):
        return FileResponse(requested_file_path, filename=safe_filename)
        
    return {"error": "Artifact not found"}, 404

@app.get("/api/executions")
def get_executions(db: Session = Depends(get_db)):
    """
    Retrieves the latest 20 executions from PostgreSQL, ordered by newest first.
    """
    # 1. Query the database
    executions = (
        db.query(models.Execution)
        .order_by(desc(models.Execution.created_at))
        .limit(20)
        .all()
    )
    
    # 2. Format the response
    result = []
    for exec_record in executions:
        # Reconstruct the artifact download URLs
        artifacts_list = []
        for art in exec_record.artifacts:
            artifacts_list.append({
                "filename": art.filename,
                "download_url": f"/api/artifacts/{exec_record.id}/{art.filename}"
            })
            
        result.append({
            "execution_id": exec_record.id,
            "prompt": exec_record.prompt,
            "status": exec_record.status,
            "output_logs": exec_record.output_logs,
            "created_at": exec_record.created_at.isoformat() if exec_record.created_at else None,
            "artifacts": artifacts_list
        })
        
    return result