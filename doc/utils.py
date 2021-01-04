import base64
from doc.responses import resp
from doc.exceptions import BizException
import random
from hashlib import md5
from time import time
from typing import Type

from rest_framework.serializers import Serializer

def now() -> int:
    return int(time() * 1000)

def digest(s: str, iter=3) -> str:
    s = md5(s.encode()).hexdigest()
    for _ in range(iter):
        s = base64.b64encode(s.encode()).decode()
    return s

def gen_valid_code(token) -> str:
    return digest(token)[:6].upper()

def val_valid_code(code, token) -> bool:
    return code == gen_valid_code(token)

def parse_email(code, nickname) -> str:
    return "{}，欢迎来到Doc Plus，您的验证码是：{}".format(nickname, code)

def gen_token() -> str:
    base = [chr(i) for i in range(128)]
    random.shuffle(base)
    return digest("".join(base) + str(now()))

def success_response(name: str):
    def foo(func):
        def bar(*args, **kwargs):
            return resp(name, func(*args, **kwargs))
        return bar
    return foo

def serialized(serializer: Type[Serializer], many=False):
    def foo(func):
        def bar(*args, **kwargs):
            data = func(*args, **kwargs)
            if data is not None:
                return serializer(data, many=many).data
            return None
        return bar
    return foo

def catch_biz_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BizException as e:
            return resp(*e.args)
    return wrapper

def api(serializer=None, many=False, success_resp_name="common.success"):
    def foo(func):
        if serializer is None:
            @catch_biz_exception
            @success_response(success_resp_name)
            def bar(*args, **kwargs):
                return func(*args, **kwargs)
        else:
            @catch_biz_exception
            @success_response(success_resp_name)
            @serialized(serializer, many)
            def bar(*args, **kwargs):
                return func(*args, **kwargs)
        return bar
    return foo
