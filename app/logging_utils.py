"""Helpers for safe logging of address PII."""

import hashlib
import os
from typing import Optional


def format_address_for_log(address: Optional[str]) -> str:
    """
    Format an address for logs without leaking PII by default.

    Returns a short SHA-256 token (plus length) unless LOG_ADDRESS_PII=full
    is set for local debugging.
    """
    if address is None or address == '':
        return '<empty>'

    if os.getenv('LOG_ADDRESS_PII', '').strip().lower() in ('1', 'true', 'yes', 'full'):
        return address

    digest = hashlib.sha256(address.encode('utf-8')).hexdigest()[:12]
    return f"addr_sha256={digest} len={len(address)}"
