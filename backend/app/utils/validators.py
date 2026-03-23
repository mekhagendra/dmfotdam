"""
Input validation utilities
"""

import re
from fastapi import HTTPException


def validate_email(email: str) -> str:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    return email


def validate_password_strength(password: str) -> str:
    """Validate password strength"""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not re.search(r'[A-Z]', password):
        raise HTTPException(status_code=400, detail="Password must contain an uppercase letter")
    if not re.search(r'[a-z]', password):
        raise HTTPException(status_code=400, detail="Password must contain a lowercase letter")
    if not re.search(r'\d', password):
        raise HTTPException(status_code=400, detail="Password must contain a digit")
    return password


def validate_url(url: str) -> str:
    """Validate URL format"""
    pattern = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
    if not re.match(pattern, url):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    return url
