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
            # If a directory is provided, mount it to the container
            if workspace_dir:
                abs_path = os.path.abspath(workspace_dir)
                # This tells Docker: "Link the Windows folder (abs_path) to /workspace inside the container"
                volumes[abs_path] = {'bind': '/workspace', 'mode': 'rw'}

            logs = self.client.containers.run(
                image=self.image_name,
                command=["python3", "-c", code_string],
                remove=True,
                network_disabled=True,
                volumes=volumes,           # Attach the folder
                working_dir="/workspace"   # Run the code inside that folder
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