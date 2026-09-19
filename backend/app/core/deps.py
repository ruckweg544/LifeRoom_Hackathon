"""
Shared FastAPI dependencies: DB session + "current member" auth.

Auth model (lightweight MVP, per spec): a member is issued an opaque
session_token when they create/join a household. The frontend stores it and
sends it as `Authorization: Bearer <token>` on every request. This dependency
resolves that token to a Member row and is the single choke point that
guarantees every household-scoped route only ever sees data for the caller's
own household - no cross-household leakage.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.member import Member
from app.core.security import hash_token

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_member(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Member:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")

    member = db.query(Member).filter(Member.session_token == hash_token(credentials.credentials)).first()
    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    return member
