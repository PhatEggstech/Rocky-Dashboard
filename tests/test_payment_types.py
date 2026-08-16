import pytest

from mcp_server.payment_types import (
    resolve_collection_document_type,
    resolve_receive_document_type,
)


def test_collection_document_type_defaults_to_existing_receive_value(monkeypatch):
    monkeypatch.delenv("MCP_PAYMENT_COLLECTION_DOCUMENT_TYPE", raising=False)
    assert resolve_collection_document_type() == 1


def test_collection_document_type_accepts_staging_candidate():
    assert resolve_collection_document_type("3") == 3


def test_receive_document_type_defaults_to_receive_value(monkeypatch):
    monkeypatch.delenv("MCP_PAYMENT_RECEIVE_DOCUMENT_TYPE", raising=False)
    assert resolve_receive_document_type() == 1


@pytest.mark.parametrize("value", ["allocate", "-1", "100"])
def test_collection_document_type_rejects_invalid_values(value):
    with pytest.raises(RuntimeError):
        resolve_collection_document_type(value)
