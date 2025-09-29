import json

# Schema enforcement filter
def enforce_schema(response: dict) -> dict:
    # Beklenen şema: {"output": str, "cache": bool}
    if not isinstance(response, dict):
        return {"output": str(response), "cache": False}
    if "output" not in response:
        response["output"] = ""
    if "cache" not in response:
        response["cache"] = False
    # Otomatik düzeltme
    response["output"] = str(response["output"])
    response["cache"] = bool(response["cache"])
    return response
