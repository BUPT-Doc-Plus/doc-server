import os
import json
from typing import Any
from rest_framework.response import Response
import easydict

config_file = "doc/errors.json"
last_modified = os.path.getmtime(config_file)

def load_config() -> dict:
    return json.loads(open(config_file, "rb").read().decode("utf-8"))

config = load_config()

def get_config() -> dict:
    global last_modified
    modified = os.path.getmtime(config_file)
    if modified == last_modified:
        return config
    last_modified = modified
    return load_config()

def r(data: Any, code=0, msg="") -> dict:
    return {
        "error": code,
        "msg": msg,
        "data": data
    }

def resp(name: str, data=None):
    info = get_config()
    for path in name.split("."):
        info = info[path]
    code, msg, status = info
    return Response(r(data, code, msg), status=status)

