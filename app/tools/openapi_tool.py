# app/agents/openapi_tool.py
import os
import json
import requests
from typing import Dict, Any
from langchain_core.tools import tool

from app.tools.utils import ToolResponse
from app.common.logger import logger
from pydantic import BaseModel

OPENAPI_DIR = os.path.join(os.path.dirname(__file__), "..", "openapi")

import subprocess
from app.common import parser

def get_token_for_external_api(fqdn):
    credential = parser.get_credentials_for_server_url(fqdn)
    endpoint = "FQDN/api/v3/auth/tokens".replace("FQDN", fqdn)
    api_client_id = credential["client_id"]
    api_client_secret = credential["client_secret"]
    command = "curl --insecure --location \'{}\' --form \'client_id=\"{}\"\' --form \'client_secret=\"{}\"\'".format(endpoint,api_client_id,api_client_secret)
    logger.info("command: {}".format(command))
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response = process.stdout.read().decode("utf-8").replace('\n', '').replace('\"', '')
    logger.info("token response: {}".format(response))
    if process.wait() == 0:
        if 'iat not satisfied' not in response:
            return response
        else:
            return False
    else:
        return False


def load_openapi_specs() -> Dict[str, Any]:
    """Load all YAML OpenAPI specs from the app/openapi directory."""
    specs = {}
    for file in os.listdir(OPENAPI_DIR):
        if file.lower().endswith((".yaml", ".yml")):
            path = os.path.join(OPENAPI_DIR, file)
            with open(path, "r", encoding="utf-8") as f:
                try:
                    spec = yaml.safe_load(f)
                    specs[file] = spec
                except Exception as e:
                    print(f"[OpenAPIAgent] Failed to parse {file}: {e}")
    return specs

from rapidfuzz import fuzz
from typing import Dict, Any

def find_missing_fields(required_fields: dict, prefilled: dict) -> dict:
    """
    Return missing url_fields and payload_fields separately.
    """
    missing = {
        "url_fields": [],
        "payload_fields": []
    }

    def walk(fields: dict, path: str, section: str):
        for k, v in fields.items():
            full_key = f"{path}.{k}" if path else k
            if k in prefilled and prefilled[k] not in (None, "", {}):
                continue
            if v is None:
                missing[section].append(full_key)
            elif isinstance(v, dict):
                if not v:
                    missing[section].append(full_key)
                else:
                    walk(v, full_key, section)
            elif isinstance(v, list):
                if not v or v == [None]:
                    missing[section].append(full_key)
                else:
                    if isinstance(v[0], dict):
                        walk(v[0], full_key + "[0]", section)

    walk(required_fields.get("url_fields", {}), "", "url_fields")
    walk(required_fields.get("payload_fields", {}), "", "payload_fields")

    return missing



def find_best_endpoint(user_prompt: str, specs: Dict[str, Any]) -> dict | None:
    """
    Find the best matching endpoint using fuzzy matching on summary, description, and operationId.
    Returns the endpoint dict with the maximum score (no threshold).
    """
    best_score = -1
    best_endpoint = None
    user_prompt_lower = user_prompt.lower()

    for filename, spec in specs.items():
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                candidates = [
                    details.get("summary", ""),
                    details.get("description", ""),
                    details.get("operationId", ""),
                ]
                # Join all candidate texts
                combined_text = " ".join(filter(None, candidates)).lower()

                if not combined_text.strip():
                    continue
                summary = details.get("summary", "")
                description = details.get("description", "")
                # Calculate fuzzy partial ratio
                score = fuzz.partial_ratio(user_prompt_lower, combined_text)
                # Keep track of max score
                if score > best_score:
                    best_score = score
                    best_endpoint = {
                        "file": filename,
                        "path": path,
                        "method": method.upper(),
                        "details": details,
                        "score": score,
                    }

    if best_score == -1:
        return None
    else:
        return best_endpoint


from typing import Dict, Any, Optional


import yaml
from typing import Union, Dict

def extract_required_fields(endpoint_details: dict, openapi_spec: Union[str, dict]) -> dict:
    """
    Extract required fields for a given endpoint:
      - url_fields (path/query parameters)
      - payload_fields (from requestBody)
    Supports resolving $ref one level deep.
    Returns dict with proper nested dicts/arrays for complex objects.
    """
    required_fields = {
        "url_fields": {},
        "payload_fields": {}
    }

    # Load YAML if path provided
    if isinstance(openapi_spec, str):
        with open(os.path.join(os.path.dirname(__file__), "../openapi", openapi_spec), "r", encoding="utf-8") as f:
            openapi_spec = yaml.safe_load(f)

    def resolve_ref(ref_path: str) -> dict:
        """Resolve a $ref path one level deep."""
        try:
            parts = ref_path.lstrip('#/').split('/')
            ref_obj = openapi_spec
            for part in parts:
                ref_obj = ref_obj.get(part, {})
            return ref_obj
        except Exception:
            return {}

    def build_field_placeholder(schema: dict):
        """Build placeholder values for objects/arrays instead of stringifying them."""
        if "$ref" in schema:
            schema = resolve_ref(schema["$ref"])

        schema_type = schema.get("type")

        if schema_type == "object":
            props = schema.get("properties", {})
            reqs = schema.get("required", [])
            return {prop: build_field_placeholder(props.get(prop, {})) for prop in reqs}
        elif schema_type == "array":
            items = schema.get("items", {})
            return [build_field_placeholder(items)]
        else:
            # primitive (string, number, boolean, etc.)
            return None

    def get_required_from_schema(schema: dict):
        """Extract required fields from a schema dict."""
        fields = {}
        if "$ref" in schema:
            schema = resolve_ref(schema["$ref"])

        props = schema.get("properties", {})
        reqs = schema.get("required", [])

        for prop in reqs:
            prop_schema = props.get(prop, {})
            # Resolve property-level $ref
            if "$ref" in prop_schema:
                prop_schema = resolve_ref(prop_schema["$ref"])
            fields[prop] = build_field_placeholder(prop_schema)
        return fields

    details = endpoint_details.get("details", {})

    # --- Handle requestBody ---
    if "requestBody" in details:
        content = details["requestBody"].get("content", {})
        for _, media in content.items():
            schema = media.get("schema", {})
            fields = get_required_from_schema(schema)
            required_fields["payload_fields"].update(fields)

    # --- Handle parameters ---
    for param in details.get("parameters", []):
        if "$ref" in param:
            param = resolve_ref(param["$ref"])

        schema = param.get("schema", {})
        if "$ref" in schema:
            schema = resolve_ref(schema["$ref"])

        if param.get("required", False):
            required_fields["url_fields"][param.get("name")] = build_field_placeholder(schema)

    return required_fields

class OpenAPIAgentToolInput(BaseModel):
    prompt: str
    base_url: str
    fields: Dict[str, Any]

def build_final_payload(required_payload_fields: dict) -> dict:
    """
    Builds the final payload.
    - Converts stringified JSON values into real objects.
    - Leaves non-JSON strings untouched.
    """
    payload = {}
    for k, v in required_payload_fields.items():
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                payload[k] = parsed
            except (ValueError, TypeError):
                payload[k] = v  # keep as string if not valid JSON
        else:
            payload[k] = v
    return payload

@tool("OpenAPIAgentTool", args_schema=OpenAPIAgentToolInput)
def openapi_tool(prompt: str, base_url: str, fields: Dict[str, Any]) -> str:
    """
    Select the best API endpoint from OpenAPI specs, prompt for missing fields
    construct payload, and execute API call.
    If tool respond with Missing required fields: in the return, stop and exit.
        "prompt": "<user natural language task>",
        "base_url": "<api base url>",
        "fields": {optional prefilled fields}
    """
    try:
        prefilled = fields or {}

        if not prompt or not base_url:
            return ToolResponse.from_error_message("Missing 'prompt' or 'base_url'")

        # Load all specs
        specs = load_openapi_specs()
        if not specs:
            return ToolResponse.from_error_message("No OpenAPI specs found in app/openapi/")

        # Find best endpoint
        endpoint = find_best_endpoint(prompt, specs)
        logger.info(f"[OpenAPIAgentTool] Found endpoint: {endpoint}")
        if not endpoint:
            return ToolResponse.from_error_message("No matching endpoint found for prompt")

        # Extract required fields
        logger.info(f"[OpenAPIAgentTool] endpoint: {endpoint}")
        required_fields = extract_required_fields(endpoint, endpoint["file"])

        # Merge with prefilled values (nested dicts)
        for section in ["url_fields", "payload_fields"]:
            if section in prefilled:
                for key, val in prefilled[section].items():
                    if key in required_fields[section]:
                        required_fields[section][key] = val
        logger.info(f"[OpenAPIAgentTool] Found required fields: {required_fields}")

        # Detect missing or placeholder fields
        missing = find_missing_fields(required_fields, prefilled)
        logger.info(f"[OpenAPIAgentTool] Missing required fields: {missing}")

        if missing["url_fields"] or missing["payload_fields"]:
            parts = []
            if missing["url_fields"]:
                parts.append("URL fields → " + ", ".join(missing["url_fields"]))
            if missing["payload_fields"]:
                parts.append("Payload fields → " + ", ".join(missing["payload_fields"]))
            missing_message = " | ".join(parts)
            return ToolResponse(
            return_message=f"Missing required fields: {missing_message}, dont proceed with calling any tool",
            missing_fields=missing
        ).json_str()

        # Build payload after validation
        payload = {}
        payload = build_final_payload(required_fields["payload_fields"])

        # Build URL
        url = base_url + endpoint["path"]
        for k, v in required_fields["url_fields"].items():
            if v is not None:
                url = url.replace(f"{{{k}}}", str(v))

        # Prepare request
        method = endpoint["method"]
        token = get_token_for_external_api(base_url)
        headers = {"Content-Type": "application/json", "Authorization": token}

        logger.info("[OpenAPIAgentTool] Sending request")

        api_request = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": payload if payload else None
        }
        logger.info(f"[OpenAPIAgentTool] Api request : {api_request}")

        # Make the request
        resp = requests.request(method, url, headers=headers, verify=False, json=payload if payload else None)
        try:
            parsed_json = resp.json()
        except Exception:
            parsed_json = None

        tool_response = ToolResponse(
            return_message="API call executed" if parsed_json else f"Non-JSON API response: {resp.text[:200]}",
            api_request={
                "url": url,
                "method": method,
                "payload": payload,
                "headers": headers
            },
            api_response=parsed_json  # Dict or None
        )
        return tool_response.json_str()

    except Exception as e:
        return ToolResponse.from_exception(e)
