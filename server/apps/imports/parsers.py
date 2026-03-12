"""
Trial Balance file parsers.

Supported formats: CSV (.csv) and Excel (.xlsx).

Each parser returns a list of dicts with at least:
  - account_number, account_name, debit, credit
  - plus raw_data (the original row as a dict)
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation

from django.core.files.uploadedfile import UploadedFile


ALLOWED_EXTENSIONS = (".csv", ".xlsx")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class ParseError(Exception):
    pass


def _to_decimal(value) -> Decimal:
    """Convert a value to Decimal, treating blanks/None as 0."""
    if value is None or str(value).strip() == "":
        return Decimal("0.00")
    try:
        return Decimal(str(value).replace(",", "").strip()).quantize(Decimal("1"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _normalize_header(header: str) -> str:
    """Lowercase + strip whitespace for fuzzy column matching."""
    return header.strip().lower().replace(" ", "_")


def _detect_columns(headers: list[str]) -> dict:
    """
    Auto-detect which columns map to account_number, account_name, debit, credit.
    Returns a mapping of our field name → column index.
    """
    normalized = [_normalize_header(h) for h in headers]

    mapping = {}
    # Account number patterns
    for pattern in ("account_number", "acct_no", "account_no", "acct_num", "account"):
        if pattern in normalized:
            mapping["account_number"] = normalized.index(pattern)
            break

    # Account name patterns
    for pattern in ("account_name", "acct_name", "description", "name"):
        if pattern in normalized:
            mapping["account_name"] = normalized.index(pattern)
            break

    # Debit
    for pattern in ("debit", "debits", "dr"):
        if pattern in normalized:
            mapping["debit"] = normalized.index(pattern)
            break

    # Credit
    for pattern in ("credit", "credits", "cr"):
        if pattern in normalized:
            mapping["credit"] = normalized.index(pattern)
            break

    # QB-style: if we found debit/credit but no account_name, check if column 0
    # is unlabeled (empty header) — it's likely the account name column.
    if "debit" in mapping and "credit" in mapping and "account_name" not in mapping:
        for i, h in enumerate(normalized):
            if h == "" and i not in mapping.values():
                mapping["account_name"] = i
                break

    return mapping


# Rows whose first-column value (lowercased) matches these are skipped as
# summary / total rows that shouldn't be imported as real TB data.
_SKIP_ROW_LABELS = frozenset(("total", "totals", "grand total", "net income"))


def _find_header_row(rows: list[list[str]]) -> int:
    """
    Scan the first several rows to find the one that looks like a header.

    A header row is one that contains at least one of 'debit', 'credit',
    'dr', 'cr'.  This handles QB exports that put a date row before the
    real header.
    """
    debit_credit_words = {"debit", "debits", "dr", "credit", "credits", "cr"}
    for idx, row in enumerate(rows[:10]):  # Only check the first 10 rows
        normalized = {_normalize_header(c) for c in row}
        if normalized & debit_credit_words:
            return idx
    return 0  # Fallback: assume first row is the header


def _is_summary_row(row_values: list) -> bool:
    """Return True if the row looks like a TOTAL / summary line."""
    first = str(row_values[0]).strip().lower() if row_values else ""
    return first in _SKIP_ROW_LABELS


def _extract_row(row_values: list, col_map: dict, row_idx: int) -> dict:
    """Extract a structured row from raw values using column mapping."""

    def _get(field, default=""):
        idx = col_map.get(field)
        if idx is not None and idx < len(row_values):
            val = row_values[idx]
            return val if val is not None else default
        return default

    return {
        "account_number": str(_get("account_number")).strip(),
        "account_name": str(_get("account_name")).strip(),
        "debit": _to_decimal(_get("debit", 0)),
        "credit": _to_decimal(_get("credit", 0)),
        "raw_data": {
            f"col_{i}": str(v) if v is not None else ""
            for i, v in enumerate(row_values)
        },
    }


def parse_csv(file: UploadedFile) -> list[dict]:
    """Parse a CSV trial balance file."""
    try:
        content = file.read().decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        raise ParseError("File is not valid UTF-8 text.")

    reader = csv.reader(io.StringIO(content))
    rows_raw = list(reader)

    if len(rows_raw) < 2:
        raise ParseError("CSV file must have a header row and at least one data row.")

    header_idx = _find_header_row(rows_raw)
    headers = rows_raw[header_idx]
    col_map = _detect_columns(headers)
    data_rows = rows_raw[header_idx + 1 :]

    parsed = []
    for idx, row in enumerate(data_rows, start=1):
        if not any(cell.strip() for cell in row):
            continue  # Skip blank rows
        if _is_summary_row(row):
            continue  # Skip TOTAL rows
        parsed.append(_extract_row(row, col_map, idx))

    return parsed


def parse_xlsx(file: UploadedFile) -> list[dict]:
    """Parse an Excel (.xlsx) trial balance file."""
    import openpyxl

    try:
        wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
    except Exception as e:
        raise ParseError(f"Could not read Excel file: {e}")

    ws = wb.active
    rows_raw = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(rows_raw) < 2:
        raise ParseError("Excel file must have a header row and at least one data row.")

    str_rows = [[str(c) if c else "" for c in row] for row in rows_raw]
    header_idx = _find_header_row(str_rows)
    headers = str_rows[header_idx]
    col_map = _detect_columns(headers)
    data_rows = str_rows[header_idx + 1 :]

    parsed = []
    for idx, row in enumerate(data_rows, start=1):
        if not any(v.strip() for v in row):
            continue
        if _is_summary_row(row):
            continue
        parsed.append(_extract_row(row, col_map, idx))

    return parsed


def parse_file(file: UploadedFile) -> list[dict]:
    """Route to the correct parser based on file extension."""
    name = file.name.lower()
    if name.endswith(".csv"):
        return parse_csv(file)
    elif name.endswith(".xlsx"):
        return parse_xlsx(file)
    else:
        raise ParseError(
            f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
