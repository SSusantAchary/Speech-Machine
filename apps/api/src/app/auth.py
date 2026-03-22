from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app import models

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    if (
        settings.local_only_mode
        and email == settings.local_admin_email
        and password == settings.local_admin_password
    ):
        return get_or_create_local_user(db)

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_or_create_local_user(db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == settings.local_admin_email).first()
    if user:
        return user
    user = models.User(
        email=settings.local_admin_email,
        hashed_password=hash_password(settings.local_admin_password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(models.User).filter(models.User.email == subject).first()
    if user is not None:
        return user
    if settings.local_only_mode and subject == settings.local_admin_email:
        return get_or_create_local_user(db)
    raise credentials_exception
