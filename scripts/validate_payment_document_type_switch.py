"""Read-only reconciliation for a PaymentOrder DocumentType switch.

Compare PaymentOrder DocumentType candidates (Receive and Allocate by default)
over the same PaymentOrder.IssueAt window before changing any MCP formula.

The database connection string is deliberately accepted only via an environment
variable. This script performs SELECT statements only and opens its transaction
as READ ONLY.

Examples:
    $env:POS_PG_DSN = 'postgresql://readonly:***@host:5432/rocky'
    python scripts/validate_payment_document_type_switch.py \
      --date-from 2026-08-01 --date-to 2026-08-05

    python scripts/validate_payment_document_type_switch.py \
      --date-from 2026-08-01 --date-to 2026-08-05 \
      --document-types 1 3 --output validation.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

import psycopg
from psycopg.rows import dict_row


DEFAULT_DSN_ENV = "POS_PG_DSN"
DEFAULT_DOCUMENT_TYPES = (1, 3)


def parse_iso_date(value: str) -> date:
    """Parse an ISO day and fail with argparse-friendly error text."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected date in YYYY-MM-DD format") from exc


def build_window(date_from: date, date_to: date) -> tuple[date, date]:
    """Return the inclusive start / exclusive end dates used by the SQL query."""
    if date_to < date_from:
        raise ValueError("date_to must be on or after date_from")
    return date_from, date_to + timedelta(days=1)


def parse_document_types(values: Sequence[str | int]) -> list[int]:
    """Normalize candidate enum values while preserving their requested order."""
    result: list[int] = []
    for value in values:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"DocumentType must be an integer: {value!r}") from exc
        if parsed < 0:
            raise ValueError("DocumentType cannot be negative")
        if parsed not in result:
            result.append(parsed)
    if not result:
        raise ValueError("At least one DocumentType is required")
    return result


SUMMARY_SQL = """
    SELECT
        po."DocumentType" AS document_type,
        COUNT(DISTINCT po."Id") AS payment_order_count,
        COUNT(poi."Id") AS payment_order_item_count,
        COUNT(DISTINCT poi."OrderId") FILTER (WHERE poi."OrderId" IS NOT NULL) AS linked_order_count,
        COUNT(poi."Id") FILTER (WHERE poi."OrderId" IS NULL) AS unlinked_item_count,
        COALESCE(SUM(poi."PaidAmount"::numeric), 0) AS paid_amount,
        COALESCE(SUM(poi."PaidAmount"::numeric) FILTER (WHERE poi."OrderId" IS NOT NULL), 0)
            AS linked_order_paid_amount,
        COALESCE(SUM(poi."PaidAmount"::numeric) FILTER (WHERE poi."OrderId" IS NULL), 0)
            AS unlinked_paid_amount
    FROM "PaymentOrder" po
    LEFT JOIN "PaymentOrderItem" poi
        ON poi."PaymentOrderId" = po."Id"
       AND poi."DeleteAt" IS NULL
       AND poi."PaidAmount" > 0
    WHERE po."CompleteAt" IS NOT NULL
      AND po."CancelAt" IS NULL
      AND po."DeleteAt" IS NULL
      AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
          BETWEEN %(date_from)s AND %(date_to)s
      AND po."DocumentType" = ANY(%(document_types)s)
    GROUP BY po."DocumentType"
    ORDER BY po."DocumentType"
"""

DAILY_SQL = """
    SELECT
        (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS issue_date,
        po."DocumentType" AS document_type,
        COUNT(DISTINCT po."Id") AS payment_order_count,
        COUNT(poi."Id") AS payment_order_item_count,
        COUNT(DISTINCT poi."OrderId") FILTER (WHERE poi."OrderId" IS NOT NULL) AS linked_order_count,
        COUNT(poi."Id") FILTER (WHERE poi."OrderId" IS NULL) AS unlinked_item_count,
        COALESCE(SUM(poi."PaidAmount"::numeric), 0) AS paid_amount,
        COALESCE(SUM(poi."PaidAmount"::numeric) FILTER (WHERE poi."OrderId" IS NOT NULL), 0)
            AS linked_order_paid_amount,
        COALESCE(SUM(poi."PaidAmount"::numeric) FILTER (WHERE poi."OrderId" IS NULL), 0)
            AS unlinked_paid_amount
    FROM "PaymentOrder" po
    LEFT JOIN "PaymentOrderItem" poi
        ON poi."PaymentOrderId" = po."Id"
       AND poi."DeleteAt" IS NULL
       AND poi."PaidAmount" > 0
    WHERE po."CompleteAt" IS NOT NULL
      AND po."CancelAt" IS NULL
      AND po."DeleteAt" IS NULL
      AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
          BETWEEN %(date_from)s AND %(date_to)s
      AND po."DocumentType" = ANY(%(document_types)s)
    GROUP BY (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date, po."DocumentType"
    ORDER BY issue_date, document_type
"""

HEADER_ALLOCATION_SQL = """
    SELECT
        po."DocumentType" AS document_type,
        COALESCE(SUM(po."AllocateAmount"::numeric), 0) AS header_allocate_amount
    FROM "PaymentOrder" po
    WHERE po."CompleteAt" IS NOT NULL
      AND po."CancelAt" IS NULL
      AND po."DeleteAt" IS NULL
      AND (po."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
          BETWEEN %(date_from)s AND %(date_to)s
      AND po."DocumentType" = ANY(%(document_types)s)
    GROUP BY po."DocumentType"
    ORDER BY po."DocumentType"
"""


def json_default(value: Any) -> Any:
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def fill_missing_candidates(rows: list[dict[str, Any]], document_types: Sequence[int]) -> list[dict[str, Any]]:
    """Include zero rows for requested candidates absent from the date range."""
    by_type = {row["document_type"]: row for row in rows}
    zero = {
        "payment_order_count": 0,
        "payment_order_item_count": 0,
        "linked_order_count": 0,
        "unlinked_item_count": 0,
        "paid_amount": Decimal("0"),
        "linked_order_paid_amount": Decimal("0"),
        "unlinked_paid_amount": Decimal("0"),
    }
    return [
        {"document_type": candidate, **by_type.get(candidate, zero)}
        for candidate in document_types
    ]


def run_validation(dsn: str, date_from: date, date_to: date, document_types: Sequence[int]) -> dict[str, Any]:
    """Run SELECT-only candidate comparisons and return a JSON-serializable report."""
    start, end_exclusive = build_window(date_from, date_to)
    params = {
        "date_from": start,
        "date_to": date_to,
        "date_to_exclusive": end_exclusive,
        "document_types": list(document_types),
    }

    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            summary_rows = connection.execute(SUMMARY_SQL, params).fetchall()
            daily_rows = connection.execute(DAILY_SQL, params).fetchall()
            header_rows = connection.execute(HEADER_ALLOCATION_SQL, params).fetchall()

    header_by_type = {
        row["document_type"]: row["header_allocate_amount"] for row in header_rows
    }
    totals = fill_missing_candidates(summary_rows, document_types)
    for total in totals:
        total["header_allocate_amount"] = header_by_type.get(
            total["document_type"], Decimal("0")
        )

    return {
        "read_only": True,
        "date_basis": "PaymentOrder.IssueAt converted to Asia/Ho_Chi_Minh date (inclusive)",
        "filters": {
            "payment_order": ["CompleteAt IS NOT NULL", "CancelAt IS NULL", "DeleteAt IS NULL"],
            "payment_order_item": ["DeleteAt IS NULL", "PaidAmount > 0"],
        },
        "range": {"date_from": start, "date_to": date_to, "date_to_exclusive": end_exclusive},
        "document_types": list(document_types),
        "totals_by_document_type": totals,
        "daily_by_document_type": daily_rows,
    }


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-from", required=True, type=parse_iso_date, help="Inclusive IssueAt day (YYYY-MM-DD)")
    parser.add_argument("--date-to", required=True, type=parse_iso_date, help="Inclusive IssueAt day (YYYY-MM-DD)")
    parser.add_argument(
        "--document-types",
        nargs="+",
        default=list(DEFAULT_DOCUMENT_TYPES),
        metavar="TYPE",
        help="Candidate PaymentOrder.DocumentType enum values (default: 1 3)",
    )
    parser.add_argument(
        "--dsn-env",
        default=DEFAULT_DSN_ENV,
        help=f"Environment variable holding the PostgreSQL DSN (default: {DEFAULT_DSN_ENV})",
    )
    parser.add_argument("--output", type=Path, help="Write JSON to this file instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        document_types = parse_document_types(args.document_types)
        build_window(args.date_from, args.date_to)
    except ValueError as exc:
        raise SystemExit(f"Argument error: {exc}") from exc

    dsn = os.environ.get(args.dsn_env)
    if not dsn:
        raise SystemExit(f"Missing required environment variable: {args.dsn_env}")

    report = run_validation(dsn, args.date_from, args.date_to, document_types)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, default=json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
        print(json.dumps({"written": str(args.output), "read_only": True}, ensure_ascii=False))
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
