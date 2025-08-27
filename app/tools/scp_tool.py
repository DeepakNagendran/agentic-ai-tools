import os
import paramiko
from  app.common.parser import get_device_ssh_credential
from pydantic import BaseModel
from app.tools.utils import ToolResponse
from langchain_core.tools import tool

def scp_download_file(ip, remote_path, local_dir="/tmp"):
    from scp import SCPClient
    local_path = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        credential = get_device_ssh_credential()
        ssh.connect(ip, username=credential['username'], password=credential['password'])

        local_filename = os.path.basename(remote_path)
        local_path = os.path.join(local_dir, local_filename)

        with SCPClient(ssh.get_transport()) as scp:
            scp.get(remote_path, local_path)

        ssh.close()
        return local_path, "File downloaded successfully"
    except Exception as e:
        return None, "File download Failed " + str(e)


# ==== SCP TOOL ====

class SCPDownloadInput(BaseModel):
    ip: str
    remote_path: str

@tool("SCPFileDownloader", args_schema=SCPDownloadInput)
def scp_tool(ip: str, remote_path: str) -> str:
    """Download a file from a remote machine via SCP using provided IP and remote_path. Returns file as status and local downloaded file path.
        "ip": "<IP mentioned in the prompt",
        "remote_path": "remote path or file location mentioned in the prompt"
    """

    if not ip or not remote_path:
        return ToolResponse.from_error_message("Missing required SSH inputs.")

    local_path, output = scp_download_file(ip=ip, remote_path=remote_path)

    return ToolResponse(
        return_message=output,
        filename=local_path
    ).json_str()
