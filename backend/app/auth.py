from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select
from app.config import SECRET_KEY, ALGORITHM
from app.database import engine
from app.models import IoTDevice

bearer = HTTPBearer()


def create_token(device_id: str, expires_days: int = 30) -> str:
    to_encode = {"sub": device_id, "exp": datetime.utcnow() + timedelta(days=expires_days)}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        device_id: str = payload.get("sub")
        if device_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return device_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def get_current_device(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> IoTDevice:
    token = credentials.credentials
    device_id = _decode_token(token)
    with Session(engine) as session:
        statement = select(IoTDevice).where(IoTDevice.device_id == device_id)
        device = session.exec(statement).first()
        if not device:
            raise HTTPException(status_code=401, detail="Device not found")
        return device
