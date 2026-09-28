# skillhub_selfhost/auth/service.py
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from skillhub_selfhost.auth.models import User

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def create_token(data: dict, secret: str, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, secret, algorithm="HS256")

def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])

async def register_user(username: str, password: str, is_admin: bool = False, status: str = "pending") -> User:
    existing = await User.filter(username=username).first()
    if existing:
        raise ValueError("用户名已存在")
    user = await User.create(
        username=username,
        password_hash=hash_password(password),
        is_admin=is_admin,
        status=status,
    )
    return user

async def login(username: str, password: str, secret: str) -> dict:
    user = await User.filter(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    if user.status == "pending":
        raise ValueError("账号尚未通过审批，请联系管理员")
    if user.status == "disabled":
        raise ValueError("账号已被禁用")

    access_token = create_token(
        {"sub": str(user.id), "username": user.username},
        secret,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_token(
        {"sub": str(user.id), "type": "refresh"},
        secret,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {"access_token": access_token, "refresh_token": refresh_token}

async def refresh_token(token: str, secret: str) -> dict:
    try:
        payload = decode_token(token, secret)
        if payload.get("type") != "refresh":
            raise ValueError()
        user_id = payload.get("sub")
        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError()
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
        raise ValueError("无效的 refresh token")

    access_token = create_token(
        {"sub": str(user.id), "username": user.username},
        secret,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = create_token(
        {"sub": str(user.id), "type": "refresh"},
        secret,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {"access_token": access_token, "refresh_token": new_refresh_token}

async def get_user_by_id(user_id: str) -> User | None:
    return await User.filter(id=user_id).first()