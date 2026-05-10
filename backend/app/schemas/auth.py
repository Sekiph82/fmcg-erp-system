from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str


class LoginResponse(BaseModel):
    """Returned by POST /auth/login. One of two shapes:
    - Normal login: access_token set, two_fa_required=False
    - 2FA required: two_fa_required=True, session_token set, method set
    """
    access_token: Optional[str] = None
    token_type: str = "bearer"
    two_fa_required: bool = False
    session_token: Optional[str] = None   # short-lived JWT for 2FA step
    method: Optional[str] = None          # totp | sms | email
    must_change_password: bool = False
