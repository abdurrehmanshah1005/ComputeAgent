# backend/worker.py
import os
from celery import Celery
from agent import CodeAgent
from sandbox import SandboxManager
from database import SessionLocal
import models

# Connect to Redis (the message broker)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=REDIS_URL)

# 3. Define the background task
@celery_app.task
def run_analysis_job(execution_id: str, prompt: str, safe_filename: str):
    # FIX: Instantiate these INSIDE the task so they don't run on import!
    agent = CodeAgent()
    sandbox = SandboxManager()
    
    workspace_dir = f"workspaces/{execution_id}"
    
    augmented_prompt = (
        f"{prompt}\n\n"
        f"Note: You have access to a file named '{safe_filename}' in your current directory. "
        "Use pandas to read it, print the desired text output, and if requested, "
        "save any visualizations as 'plot.png' or reports as 'analysis.xlsx'."
    )
    
    try:
        generated_code = agent.generate_python_code(augmented_prompt)
        execution_result = sandbox.execute_code(generated_code, workspace_dir=workspace_dir)
    except Exception as e:
        generated_code = "Failed to generate code."
        execution_result = {"status": "error", "output": str(e)}

    # 4. Update the database when finished
    db = SessionLocal()
    try:
        db_execution = db.query(models.Execution).filter(models.Execution.id == execution_id).first()
        if db_execution:
            db_execution.generated_code = generated_code
            db_execution.status = execution_result["status"]
            db_execution.output_logs = execution_result["output"]
            
            # Scan for artifacts
            if os.path.exists(workspace_dir):
                for filename in os.listdir(workspace_dir):
                    if filename != safe_filename:
                        db.add(models.Artifact(execution_id=execution_id, filename=filename))
            
            db.commit()
    finally:
        db.close()