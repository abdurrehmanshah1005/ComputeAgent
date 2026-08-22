# backend/sandbox.py
import docker

class SandboxManager:
    def __init__(self):
        self.client = docker.from_env()
        self.image_name = "computeagent-sandbox:latest"

    def execute_code(self, code_string: str):
        try:
            # 1. Start a temporary container (removed the invalid argument)
            # When detach=False (default), it waits for the container to finish 
            # and directly returns the terminal output as bytes.
            logs = self.client.containers.run(
                image=self.image_name,
                command=["python3", "-c", code_string],
                remove=True,
                network_disabled=True 
            )
            
            # 2. Return the printed output
            return {
                "status": "success",
                "output": logs.decode("utf-8").strip()
            }

        except docker.errors.ContainerError as e:
            return {
                "status": "error",
                "output": e.stderr.decode("utf-8").strip()
            }
        except docker.errors.ImageNotFound:
            return {
                "status": "error",
                "output": f"Docker image '{self.image_name}' not found. Did we build it?"
            }