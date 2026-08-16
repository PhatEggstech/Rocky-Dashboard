"""Configuration helpers for POS payment document types."""
from __future__ import annotations

import os


DEFAULT_COLLECTION_DOCUMENT_TYPE = 1
DEFAULT_RECEIVE_DOCUMENT_TYPE = 1


def resolve_collection_document_type(raw_value: str | None = None) -> int:
    """Return the configured collection document type as a bounded integer."""
    raw_value = raw_value if raw_value is not None else os.environ.get(
        "MCP_PAYMENT_COLLECTION_DOCUMENT_TYPE",
        str(DEFAULT_COLLECTION_DOCUMENT_TYPE),
    )
    try:
        document_type = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "MCP_PAYMENT_COLLECTION_DOCUMENT_TYPE must be an integer"
        ) from exc
    if not 0 <= document_type <= 99:
        raise RuntimeError(
            "MCP_PAYMENT_COLLECTION_DOCUMENT_TYPE must be between 0 and 99"
        )
    return document_type


def resolve_receive_document_type(raw_value: str | None = None) -> int:
    """Return the legacy Receive type used only as a per-order fallback."""
    raw_value = raw_value if raw_value is not None else os.environ.get(
        "MCP_PAYMENT_RECEIVE_DOCUMENT_TYPE",
        str(DEFAULT_RECEIVE_DOCUMENT_TYPE),
    )
    try:
        document_type = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "MCP_PAYMENT_RECEIVE_DOCUMENT_TYPE must be an integer"
        ) from exc
    if not 0 <= document_type <= 99:
        raise RuntimeError(
            "MCP_PAYMENT_RECEIVE_DOCUMENT_TYPE must be between 0 and 99"
        )
    return document_type
