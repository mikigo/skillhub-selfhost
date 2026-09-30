# skillhub_selfhost/skills/errors.py
"""skills 域的异常。

ValidationError / ConflictError 故意继承 ValueError：既有的 `except ValueError`
分支和现存测试因此行为不变，路由可以逐步迁移到更精确的类型。
RemoteFetchError 不继承 ValueError，避免被旧的 `except ValueError -> 404` 吞掉。
"""


class ValidationError(ValueError):
    """输入不合法 → 400"""


class ConflictError(ValueError):
    """与已有数据冲突 → 409"""


class RemoteFetchError(Exception):
    """上游（GitLab）访问失败，自带应当返回的 HTTP 状态码。"""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
