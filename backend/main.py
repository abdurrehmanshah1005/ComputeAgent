# backend/main.py
from fastapi import FastAPI,UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
import os
import uuid

from pydantic import BaseModel
from dotenv import load_dotenv

# Load the .env file so the API key is available
load_dotenv()

from sandbox import SandboxManager
from agent import CodeAgent

app = FastAPI(title="ComputeAgent API")

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
    file: UploadFile = File(...)
):
    """
    1. Saves the uploaded file to a temporary unique folder.
    2. Tells the AI the filename so it can write pandas code.
    3. Mounts the folder to the Docker container and executes the code.
    """
    # Create a unique directory for this specific execution
    execution_id = str(uuid.uuid4())
    workspace_dir = f"workspaces/{execution_id}"
    os.makedirs(workspace_dir, exist_ok=True)

    # Save the uploaded file into this directory
    file_path = os.path.join(workspace_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Augment the prompt so the AI knows the file exists
    augmented_prompt = (
        f"{prompt}\n\n"
        f"Note: You have access to a file named '{file.filename}' in your current directory. "
        "Use pandas to read it and print the desired output."
    )

    try:
        generated_code = agent.generate_python_code(augmented_prompt)
    except Exception as e:
        return {"status": "api_error", "message": str(e)}

    # Execute the code, passing the workspace_dir so Docker mounts it
    execution_result = sandbox.execute_code(generated_code, workspace_dir=workspace_dir)

    return {
        "execution_id": execution_id,
        "prompt": augmented_prompt,
        "generated_code": generated_code,
        "execution": execution_result
    }

@app.post("/api/analyze")
def analyze_file(
    prompt: str = Form(...), 
    file: UploadFile = File(...)
):
    execution_id = str(uuid.uuid4())
    workspace_dir = f"workspaces/{execution_id}"
    os.makedirs(workspace_dir, exist_ok=True)

    # 1. Save the uploaded file
    file_path = os.path.join(workspace_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Augment prompt
    augmented_prompt = (
        f"{prompt}\n\n"
        f"Note: You have access to a file named '{file.filename}' in your current directory. "
        "Use pandas to read it, print the desired text output, and if requested, "
        "save any visualizations as 'plot.png' or reports as 'analysis.xlsx'."
    )

    try:
        generated_code = agent.generate_python_code(augmented_prompt)
    except Exception as e:
        return {"status": "api_error", "message": str(e)}

    # 3. Execute code in Docker
    execution_result = sandbox.execute_code(generated_code, workspace_dir=workspace_dir)

    # 4. Collect any generated files (Artifacts)
    # We look for everything in the workspace EXCEPT the input file the user uploaded
    artifacts = []
    if os.path.exists(workspace_dir):
        for filename in os.listdir(workspace_dir):
            if filename != file.filename:
                artifacts.append({
                    "filename": filename,
                    "download_url": f"/api/artifacts/{execution_id}/{filename}"
                })

    return {
        "execution_id": execution_id,
        "generated_code": generated_code,
        "execution": execution_result,
        "artifacts": artifacts
    }

@app.get("/api/artifacts/{execution_id}/{filename}")
def download_artifact(execution_id: str, filename: str):
    """
    Safely serves generated files (like PNGs or Excel sheets) back to the user.
    """
    file_path = os.path.join("workspaces", execution_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return {"error": "Artifact not found"}, 404