from pydantic import BaseModel
from typing import Optional, Dict, Any


class ToolResponse(BaseModel):
    return_message: str = None
    filename: Optional[str] = None
    api_request: Optional[Dict[str, Any]] = None
    api_response: Optional[Dict[str, Any]] = None
    endpoint: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None
    missing_fields: Optional[Dict[str, Any]] = None

    def json_str(self):
        """Return JSON string representation compatible with both Pydantic v1 and v2."""
        try:
            return self.model_dump_json()  # pydantic v2
        except AttributeError:
            return self.json()  # pydantic v1

    @staticmethod
    def from_exception(exc: Exception, prefix: str = "[Tool Error]") -> str:
        """Helper to return error as a JSON string"""
        return ToolResponse(return_message=f"{prefix} {str(exc)}").json_str()

    @staticmethod
    def from_error_message(msg: str, prefix: str = "[Tool Error]") -> str:
        """Helper to return plain error string as valid JSON"""
        return ToolResponse(return_message=f"{prefix} {msg}").json_str()

    @staticmethod
    def safe_parse(raw: str) -> "ToolResponse":
        """Safe parse from raw string, returns ToolResponse with raw fallback"""
        try:
            return ToolResponse.parse_raw(raw)
        except Exception as e:
            return ToolResponse(return_message=f"[Tool Output Parsing Error] {str(e)}\nRaw: {raw}")
