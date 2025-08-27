import json
from urllib.parse import urlparse
from app.common.logger import logger

def load_json_file(json_path="app/configs/server_client_secret.json"):
    with open(json_path, "r") as f:
        return json.load(f)


def get_domain(url):
    parsed = urlparse(url)
    return parsed.netloc


def get_credentials_for_server_url(url):
    credentials_data = load_json_file("app/configs/server_client_secret.json")
    domain = get_domain(url)
    logger.info("Getting credentials for server url {}".format(url))
    auth_servers = credentials_data.get("auth_servers", {})

    if domain in auth_servers:
        return auth_servers[domain]
    else:
        raise ValueError(f"No credentials found for domain: {domain}")

def get_device_ssh_credential():
    credentials_data = load_json_file("app/configs/device_credential.json")
    credential = credentials_data.get("ece_ssh_credential")
    if credential:
        return credential
    else:
        raise ValueError(f"No credentials found for ECE")

