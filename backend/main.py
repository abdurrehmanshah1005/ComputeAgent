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
    db: Session = Depends(get_db)  # <-- INJECT THE DATABASE SESSION
):
    execution_id = str(uuid.uuid4())
    workspace_dir = f"workspaces/{execution_id}"
    os.makedirs(workspace_dir, exist_ok=True)

    safe_filename = secure_filename(file.filename)
    file_path = os.path.join(workspace_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    augmented_prompt = (
        f"{prompt}\n\n"
        f"Note: You have access to a file named '{safe_filename}' in your current directory. "
        "Use pandas to read it, print the desired text output, and if requested, "
        "save any visualizations as 'plot.png' or reports as 'analysis.xlsx'."
    )

    try:
        generated_code = agent.generate_python_code(augmented_prompt)
    except Exception as e:
        return {"status": "api_error", "message": str(e)}

    execution_result = sandbox.execute_code(generated_code, workspace_dir=workspace_dir)

    # ---------------------------------------------------------
    # DATABASE STEP 1: Save the Execution record
    # ---------------------------------------------------------
    db_execution = models.Execution(
        id=execution_id,
        prompt=augmented_prompt,
        generated_code=generated_code,
        status=execution_result["status"],
        output_logs=execution_result["output"]
    )
    db.add(db_execution)
    # We must commit now so the Execution exists in the DB before we link Artifacts to it
    db.commit() 

    artifacts = []
    if os.path.exists(workspace_dir):
        for filename in os.listdir(workspace_dir):
            if filename != safe_filename:
                # ---------------------------------------------------------
                # DATABASE STEP 2: Save the Artifact records
                # ---------------------------------------------------------
                db_artifact = models.Artifact(
                    execution_id=execution_id,
                    filename=filename
                )
                db.add(db_artifact)
                
                artifacts.append({
                    "filename": filename,
                    "download_url": f"/api/artifacts/{execution_id}/{filename}"
                })
    
    # Commit all the new artifact records to the database
    db.commit()

    return {
        "execution_id": execution_id,
        "generated_code": generated_code,
        "execution": execution_result,
        "artifacts": artifacts
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
            "created_at": exec_record.created_at.isoformat() if exec_record.created_at else None,
            "artifacts": artifacts_list
        })
        
    return result