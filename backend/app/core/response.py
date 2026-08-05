from typing import Any


def success_response(data: Any):
    return {"success": True, "data": data, "error": None}


def error_response(code: str, message: str):
    return {"success": False, "data": None, "error": {"code": code, "message": message}}
