# backend/sandbox.py
import docker
import os

class SandboxManager:
    def __init__(self):
        self.client = docker.from_env()
        self.image_name = "computeagent-sandbox:latest"

    def execute_code(self, code_string: str, workspace_dir: str = None):
        try:
            volumes = {}
            working_dir = "/"
            
            if workspace_dir:
                # Extract the UUID (e.g., "workspaces/123-uuid" -> "123-uuid")
                execution_id = workspace_dir.split("/")[-1]
                
                # Use the Docker named volume instead of a local host path
                volumes['shared_workspaces'] = {'bind': '/sandbox_data', 'mode': 'rw'}
                working_dir = f"/sandbox_data/{execution_id}"

            logs = self.client.containers.run(
                image=self.image_name,
                command=["python3", "-c", code_string],
                remove=True,
                network_disabled=True,
                volumes=volumes,
                working_dir=working_dir
            )
            
            return {
                "status": "success",
                "output": logs.decode("utf-8").strip()
            }

        except docker.errors.ContainerError as e:
            return {
                "status": "error",
                "output": e.stderr.decode("utf-8").strip()
            }
        except Exception as e:
            # Catch APIErrors (like invalid mounts) so they are safely returned
            return {
                "status": "error",
                "output": f"Sandbox infrastructure error: {str(e)}"
            }