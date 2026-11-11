"""Bank statement file parsers: ISO 20022 camt.053, SWIFT MT940, OFX and CSV.

Each parser turns the file a bank exports into a ``ParsedStatement`` whose lines match
``BRStatementLineCreate`` (positive amount + C/D indicator). Parsers never guess missing
balances: the importer checks opening + credits - debits == closing before persisting.
"""
from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

MAX_STATEMENT_BYTES = 5 * 1024 * 1024


class StatementParseError(ValueError):
    pass


@dataclass
class ParsedStatement:
    format: str
    account: Optional[str] = None
    currency: Optional[str] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    statement_date: Optional[date] = None
    lines: list[dict] = field(default_factory=list)

    def totals(self) -> tuple[Decimal, Decimal]:
        credits = sum((Decimal(str(l["amount"])) for l in self.lines if l["debit_credit_indicator"] == "C"), Decimal("0"))
        debits = sum((Decimal(str(l["amount"])) for l in self.lines if l["debit_credit_indicator"] == "D"), Decimal("0"))
        return credits, debits

    def fill_period_from_lines(self) -> None:
        dates = [l["transaction_date"] for l in self.lines]
        if dates:
            self.period_start = self.period_start or min(dates)
            self.period_end = self.period_end or max(dates)
        self.statement_date = self.statement_date or self.period_end


def _decimal(raw: str, *, comma_decimal: bool = False) -> Decimal:
    text = (raw or "").strip().replace(" ", "")
    if comma_decimal:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise StatementParseError(f"Invalid amount {raw!r}") from exc
    if not value.is_finite():
        raise StatementParseError(f"Invalid amount {raw!r}")
    return value


def _line(tx_date: date, amount: Decimal, *, value_date=None, reference=None, bank_reference=None,
          narration=None, counterparty=None, balance=None) -> dict:
    return {
        "transaction_date": tx_date,
        "value_date": value_date,
        "external_reference": (reference or None) and reference[:100],
        "bank_reference": (bank_reference or None) and bank_reference[:100],
        "narration": (narration or None) and narration[:500],
        "counterparty_name": (counterparty or None) and counterparty[:255],
        "amount": float(abs(amount)),
        "debit_credit_indicator": "D" if amount < 0 else "C",
        "running_balance": float(balance) if balance is not None else None,
    }


# ── ISO 20022 camt.053 ───────────────────────────────────────────────────────

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(node, path: str):
    """Namespace-agnostic child lookup: path like 'Acct/Id/IBAN'."""
    current = [node]
    for part in path.split("/"):
        current = [child for n in current for child in list(n) if _local(child.tag) == part]
        if not current:
            return None
    return current[0]


def _findall(node, name: str):
    return [child for child in list(node) if _local(child.tag) == name]


def _text(node, path: str) -> Optional[str]:
    found = _find(node, path)
    return found.text.strip() if found is not None and found.text else None


def _iso_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    return date.fromisoformat(raw[:10])


def parse_camt053(data: bytes) -> ParsedStatement:
    if b"<!DOCTYPE" in data[:4096].upper() or b"<!ENTITY" in data.upper():
        raise StatementParseError("XML with DOCTYPE/ENTITY declarations is not accepted.")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise StatementParseError(f"Not valid XML: {exc}") from exc
    stmts = [n for n in root.iter() if _local(n.tag) == "Stmt"]
    if len(stmts) != 1:
        raise StatementParseError(f"Expected exactly one <Stmt>, found {len(stmts)}; import one statement per file.")
    stmt = stmts[0]
    parsed = ParsedStatement(format="CAMT053")
    parsed.account = _text(stmt, "Acct/Id/IBAN") or _text(stmt, "Acct/Id/Othr/Id")
    parsed.currency = _text(stmt, "Acct/Ccy")
    for bal in _findall(stmt, "Bal"):
        code = _text(bal, "Tp/CdOrPrtry/Cd")
        amount = _decimal(_text(bal, "Amt") or "")
        if _text(bal, "CdtDbtInd") == "DBIT":
            amount = -amount
        if code in {"OPBD", "PRCD"} and parsed.opening_balance is None:
            parsed.opening_balance = amount
        elif code == "CLBD":
            parsed.closing_balance = amount
            parsed.statement_date = _iso_date(_text(bal, "Dt/Dt") or _text(bal, "Dt/DtTm"))
    parsed.period_start = _iso_date(_text(stmt, "FrToDt/FrDtTm") or _text(stmt, "FrToDt/FrDt"))
    parsed.period_end = _iso_date(_text(stmt, "FrToDt/ToDtTm") or _text(stmt, "FrToDt/ToDt"))
    for entry in _findall(stmt, "Ntry"):
        status = _text(entry, "Sts/Cd") or _text(entry, "Sts")
        if status and status != "BOOK":
            continue  # pending/information entries are not booked movements
        amount = _decimal(_text(entry, "Amt") or "")
        debit = _text(entry, "CdtDbtInd") == "DBIT"
        if _text(entry, "RvslInd") == "true":
            debit = not debit
        booked = _iso_date(_text(entry, "BookgDt/Dt") or _text(entry, "BookgDt/DtTm"))
        if booked is None:
            raise StatementParseError("A booked entry has no booking date.")
        tx = _find(entry, "NtryDtls/TxDtls")
        counterparty = None
        reference = None
        narration = _text(entry, "AddtlNtryInf")
        if tx is not None:
            counterparty = _text(tx, "RltdPties/Cdtr/Nm" if debit else "RltdPties/Dbtr/Nm") or _text(
                tx, "RltdPties/Cdtr/Pty/Nm" if debit else "RltdPties/Dbtr/Pty/Nm")
            reference = _text(tx, "Refs/EndToEndId") or _text(tx, "Refs/InstrId")
            if reference == "NOTPROVIDED":
                reference = None
            narration = _text(tx, "RmtInf/Ustrd") or narration
        parsed.lines.append(_line(
            booked, -amount if debit else amount,
            value_date=_iso_date(_text(entry, "ValDt/Dt") or _text(entry, "ValDt/DtTm")),
            reference=reference, bank_reference=_text(entry, "AcctSvcrRef") or _text(entry, "NtryRef"),
            narration=narration, counterparty=counterparty,
        ))
    return parsed


# ── SWIFT MT940 ──────────────────────────────────────────────────────────────

_MT940_LINE = re.compile(
    r"^(?P<value>\d{6})(?P<entry>\d{4})?(?P<mark>R?[CD])(?P<funds>[A-Z])?(?P<amount>\d+,\d*)"
    r"(?P<type>[A-Z0-9]{4})(?P<ref>[^/\n]*)(?://(?P<bankref>[^\n]*))?"
)
_MT940_BAL = re.compile(r"^(?P<mark>[CD])(?P<date>\d{6})(?P<ccy>[A-Z]{3})(?P<amount>\d+,\d*)")


def _yymmdd(raw: str) -> date:
    return datetime.strptime(raw, "%y%m%d").date()


def _mt940_fields(text: str) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        match = re.match(r"^:(\d{2}[A-Z]?):(.*)$", line)
        if match:
            fields.append((match.group(1), match.group(2)))
        elif fields and line and not line.startswith(("-}", "{", "-")):
            tag, value = fields[-1]
            fields[-1] = (tag, value + "\n" + line)
    return fields


def parse_mt940(data: bytes) -> ParsedStatement:
    text = data.decode("utf-8", errors="replace")
    fields = _mt940_fields(text)
    if not any(tag.startswith("61") for tag, _ in fields) and not any(tag.startswith("60") for tag, _ in fields):
        raise StatementParseError("No MT940 :60: or :61: fields found.")
    if sum(1 for tag, _ in fields if tag in {"60F", "60M"}) > 1:
        raise StatementParseError("The file holds several MT940 statements; import one statement per file.")
    parsed = ParsedStatement(format="MT940")
    pending: Optional[dict] = None
    for tag, value in fields:
        if tag == "25":
            parsed.account = value.strip()
        elif tag in {"60F", "60M"}:
            m = _MT940_BAL.match(value.strip())
            if not m:
                raise StatementParseError(f"Unreadable opening balance :{tag}:{value}")
            amount = _decimal(m["amount"], comma_decimal=True)
            parsed.opening_balance = -amount if m["mark"] == "D" else amount
            parsed.currency = m["ccy"]
            parsed.period_start = _yymmdd(m["date"])
        elif tag in {"62F", "62M"}:
            m = _MT940_BAL.match(value.strip())
            if not m:
                raise StatementParseError(f"Unreadable closing balance :{tag}:{value}")
            amount = _decimal(m["amount"], comma_decimal=True)
            parsed.closing_balance = -amount if m["mark"] == "D" else amount
            parsed.statement_date = _yymmdd(m["date"])
            parsed.period_end = parsed.statement_date
        elif tag == "61":
            first, _, extra = value.partition("\n")
            m = _MT940_LINE.match(first.strip())
            if not m:
                raise StatementParseError(f"Unreadable statement line :61:{first}")
            value_date = _yymmdd(m["value"])
            entry_date = value_date
            if m["entry"]:
                entry_date = date(value_date.year, int(m["entry"][:2]), int(m["entry"][2:]))
                if (entry_date - value_date).days > 180:
                    entry_date = entry_date.replace(year=entry_date.year - 1)
                elif (value_date - entry_date).days > 180:
                    entry_date = entry_date.replace(year=entry_date.year + 1)
            amount = _decimal(m["amount"], comma_decimal=True)
            debit = m["mark"] in {"D", "RC"}  # RC = reversal of credit, RD = reversal of debit
            ref = (m["ref"] or "").strip()
            pending = _line(entry_date, -amount if debit else amount, value_date=value_date,
                            reference=None if ref in {"", "NONREF"} else ref,
                            bank_reference=(m["bankref"] or "").strip() or None, narration=extra.strip() or None)
            parsed.lines.append(pending)
        elif tag == "86" and pending is not None:
            info = " ".join(part.strip() for part in value.split("\n") if part.strip())
            pending["narration"] = info[:500] or pending["narration"]
    return parsed


# ── OFX (SGML 1.x or XML 2.x) ────────────────────────────────────────────────

def _ofx_tag(block: str, tag: str) -> Optional[str]:
    m = re.search(rf"<{tag}>([^<\r\n]*)", block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def _ofx_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    return datetime.strptime(raw[:8], "%Y%m%d").date()


def parse_ofx(data: bytes) -> ParsedStatement:
    text = data.decode("utf-8", errors="replace")
    if "<OFX>" not in text.upper():
        raise StatementParseError("Not an OFX file (no <OFX> element).")
    if len(re.findall(r"<STMTRS>", text, flags=re.IGNORECASE)) > 1:
        raise StatementParseError("The file holds several OFX statements; import one statement per file.")
    parsed = ParsedStatement(format="OFX")
    parsed.account = _ofx_tag(text, "ACCTID")
    parsed.currency = _ofx_tag(text, "CURDEF")
    parsed.period_start = _ofx_date(_ofx_tag(text, "DTSTART"))
    parsed.period_end = _ofx_date(_ofx_tag(text, "DTEND"))
    ledger = re.search(r"<LEDGERBAL>(.*?)(</LEDGERBAL>|<AVAILBAL>|</STMTRS>)", text, flags=re.IGNORECASE | re.DOTALL)
    if ledger:
        parsed.closing_balance = _decimal(_ofx_tag(ledger.group(1), "BALAMT") or "")
        parsed.statement_date = _ofx_date(_ofx_tag(ledger.group(1), "DTASOF"))
    for block in re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|(?=</BANKTRANLIST>))", text,
                            flags=re.IGNORECASE | re.DOTALL):
        posted = _ofx_date(_ofx_tag(block, "DTPOSTED"))
        if posted is None:
            raise StatementParseError("An OFX transaction has no DTPOSTED.")
        name = _ofx_tag(block, "NAME")
        memo = _ofx_tag(block, "MEMO")
        parsed.lines.append(_line(
            posted, _decimal(_ofx_tag(block, "TRNAMT") or ""),
            value_date=_ofx_date(_ofx_tag(block, "DTAVAIL")), reference=_ofx_tag(block, "CHECKNUM"),
            bank_reference=_ofx_tag(block, "FITID"), narration=memo or name, counterparty=name,
        ))
    if parsed.closing_balance is not None:
        credits, debits = parsed.totals()
        # OFX carries only the ledger balance; the opening balance follows from the movements.
        parsed.opening_balance = parsed.closing_balance - credits + debits
    return parsed


# ── CSV ──────────────────────────────────────────────────────────────────────

_CSV_COLUMNS = {
    "date": ("transaction date", "trans date", "date", "posting date", "booking date", "txn date", "tran date"),
    "value_date": ("value date", "val date"),
    "narration": ("description", "narration", "narrative", "details", "particulars", "transaction details", "memo"),
    "reference": ("reference", "ref", "customer reference", "cheque no", "cheque number", "transaction id"),
    "bank_reference": ("bank reference", "bank ref", "receipt no", "receipt no.", "fitid"),
    "counterparty": ("counterparty", "beneficiary", "payee", "payer", "name"),
    "debit": ("debit", "debits", "withdrawal", "withdrawals", "money out", "paid out", "dr"),
    "credit": ("credit", "credits", "deposit", "deposits", "money in", "paid in", "cr"),
    "amount": ("amount", "transaction amount"),
    "balance": ("balance", "running balance", "closing balance", "book balance"),
}
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d-%b-%Y", "%d/%m/%y", "%Y/%m/%d")


def _csv_date(raw: str) -> date:
    text = (raw or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise StatementParseError(f"Unrecognised date {raw!r} (use YYYY-MM-DD or DD/MM/YYYY).")


def parse_csv(data: bytes) -> ParsedStatement:
    text = data.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    header_index = next((i for i, row in enumerate(rows[:20])
                         if any(c.strip().lower() in _CSV_COLUMNS["date"] for c in row)), None)
    if header_index is None:
        raise StatementParseError("No header row with a date column found in the first 20 rows.")
    header = [c.strip().lower() for c in rows[header_index]]
    col = {key: next((header.index(n) for n in names if n in header), None) for key, names in _CSV_COLUMNS.items()}
    if col["amount"] is None and (col["debit"] is None or col["credit"] is None):
        raise StatementParseError("Need an Amount column or both Debit and Credit columns.")
    parsed = ParsedStatement(format="CSV")
    for row in rows[header_index + 1:]:
        if not any(cell.strip() for cell in row) or col["date"] >= len(row) or not row[col["date"]].strip():
            continue

        def cell(key):
            idx = col[key]
            return row[idx].strip() if idx is not None and idx < len(row) else ""

        if col["amount"] is not None and cell("amount"):
            amount = _decimal(cell("amount"))
        else:
            amount = (_decimal(cell("credit")) if cell("credit") else Decimal("0")) - (
                _decimal(cell("debit")) if cell("debit") else Decimal("0"))
        if amount == 0:
            continue
        balance = _decimal(cell("balance")) if cell("balance") else None
        parsed.lines.append(_line(
            _csv_date(cell("date")), amount,
            value_date=_csv_date(cell("value_date")) if cell("value_date") else None,
            reference=cell("reference") or None, bank_reference=cell("bank_reference") or None,
            narration=cell("narration") or None, counterparty=cell("counterparty") or None, balance=balance,
        ))
    if parsed.lines and parsed.lines[0]["transaction_date"] > parsed.lines[-1]["transaction_date"]:
        parsed.lines.reverse()  # many banks export newest first
    first, last = (parsed.lines[0], parsed.lines[-1]) if parsed.lines else (None, None)
    if first and first["running_balance"] is not None and last["running_balance"] is not None:
        # Running balances give both ends of the statement.
        signed = Decimal(str(first["amount"])) * (-1 if first["debit_credit_indicator"] == "D" else 1)
        parsed.opening_balance = Decimal(str(first["running_balance"])) - signed
        parsed.closing_balance = Decimal(str(last["running_balance"]))
    return parsed


PARSERS = {"CAMT053": parse_camt053, "MT940": parse_mt940, "OFX": parse_ofx, "CSV": parse_csv}


def parse_statement(fmt: str, data: bytes) -> ParsedStatement:
    if len(data) > MAX_STATEMENT_BYTES:
        raise StatementParseError("Statement files are limited to 5 MB.")
    parser = PARSERS.get(fmt.upper())
    if parser is None:
        raise StatementParseError(f"Unsupported format {fmt!r}; use one of {sorted(PARSERS)}.")
    parsed = parser(data)
    if not parsed.lines:
        raise StatementParseError("The statement contains no booked transactions.")
    parsed.fill_period_from_lines()
    return parsed
