
import os
import secrets
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

import database

load_dotenv()

API_KEY = os.environ.get("API_KEY", "")
LIBRARIAN_CARDS = {
    card.strip() for card in os.environ.get("LIBRARIAN_CARDS", "").split(",") 
    if card.strip()
    }

api_key_header = APIKeyHeader(
    name="X-API-Key", scheme_name="API key", auto_error=False
    )
card_header = APIKeyHeader(
    name="X-Card-Number", scheme_name="Member card", auto_error=False
    )


def require_api_key(key: Annotated[str | None, Depends(api_key_header)]) -> None:
    if (not API_KEY or not key 
        or not secrets.compare_digest(key.encode(), API_KEY.encode())):
            raise HTTPException(status_code=401, detail="Missing or invalid API key")


def get_current_member(
    _key_checked: Annotated[None, Depends(require_api_key)], 
    card: Annotated[str | None, Depends(card_header)]
    ) -> dict:
    member = database.find_member_by_card(card) if card else None
    if member is None:
        raise HTTPException(status_code=401, detail="Unknown card")
    role = "librarian" if member["card_number"] in LIBRARIAN_CARDS else "member"
    return {**member, "role": role}


def require_librarian(member: Annotated[dict, Depends(get_current_member)]) -> dict:
    if member["role"] != "librarian":
        raise HTTPException(status_code=403, detail="Librarian access required")
    return member
