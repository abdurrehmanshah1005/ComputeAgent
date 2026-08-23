# backend/main.py
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

import shutil
import os
import uuid
import re
from pathlib import Path
from dotenv import load_dotenv

# Import our database dependencies
from database import get_db, engine
import models
from worker import run_analysis_job

# Load the .env file so the API key is available
load_dotenv()

app = FastAPI(title="ComputeAgent API")

# Create the tables in the database
models.Base.metadata.create_all(bind=engine)

def secure_filename(filename: str) -> str:
    """
    Strips directory paths and removes dangerous characters.
    '../../../etc/passwd' becomes 'passwd'
    """
    base_name = Path(filename).name 
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
    return safe_name if safe_name else "uploaded_file"


@app.get("/health")
def health_check():
    return {"status": "ok"}


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
        status="queued",
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
    if not re.match(r'^[a-f0-9-]+$', execution_id):
        return {"error": "Invalid execution ID"}, 400

    workspace_dir = os.path.abspath(os.path.join("workspaces", execution_id))
    safe_filename = secure_filename(filename)
    requested_file_path = os.path.abspath(os.path.join(workspace_dir, safe_filename))

    # SECURITY FIX: Ensure the requested file path starts strictly with the workspace path.
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
    executions = (
        db.query(models.Execution)
        .order_by(desc(models.Execution.created_at))
        .limit(20)
        .all()
    )
    
    result = []
    for exec_record in executions:
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