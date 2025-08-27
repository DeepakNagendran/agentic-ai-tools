import paramiko
from  app.common.parser import get_ece_ssh_credential
from pydantic import BaseModel
from app.tools.utils import ToolResponse
from langchain_core.tools import tool

def execute_ssh_command(ip: str, command: str) -> str:
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        credential = get_ece_ssh_credential()
        ssh.connect(ip, username=credential['username'], password=credential['password'])
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        ssh.close()
        return output if output else error
    except Exception as e:
        return f"SSH Error: {str(e)}"


# ==== SSH TOOL ====
class SSHCommandInput(BaseModel):
    ip: str
    command: str

@tool("SSHCommandExecutor", args_schema=SSHCommandInput)
def ssh_tool(ip: str, command: str) -> str:
    """Execute a command on a remote machine via SSH using provided IP, and command.
        "ip": "<IP mentioned in the prompt",
        "command": "command mentioned in the prompt
    """
    if not ip or not command:
        return ToolResponse.from_error_message("Missing required SSH inputs.")

    output = execute_ssh_command(ip=ip, command=command)
    return ToolResponse(return_message=output).json_str()