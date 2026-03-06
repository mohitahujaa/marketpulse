"""
Unified response envelope: {success, data, message}
Keeps all API responses consistent — easier for frontend to handle.
"""
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


def success_response(
    data: Any = None,
    message: str = "OK",
    status_code: int = 200,
) -> JSONResponse:
    """
    Wrap any data in a standard success envelope.

    Example:
        {"success": true, "message": "Login successful.", "data": {...}}
    """
    content: dict[str, Any] = {"success": True, "message": message}
    if data is not None:
        # Serialize Pydantic models to dicts
        if isinstance(data, BaseModel):
            content["data"] = data.model_dump(mode="json")
        elif isinstance(data, list):
            content["data"] = [
                item.model_dump(mode="json") if isinstance(item, BaseModel) else item
                for item in data
            ]
        else:
            content["data"] = data

    return JSONResponse(status_code=status_code, content=content)
