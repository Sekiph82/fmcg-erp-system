"""Bank statement file parsers: camt.053, MT940, OFX and CSV (synthetic sample files)."""
from datetime import date
from decimal import Decimal

import pytest

from app.services.bank_statement_parsers import StatementParseError, parse_statement

CAMT053 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
 <BkToCstmrStmt>
  <GrpHdr><MsgId>STMT-SYN-1</MsgId><CreDtTm>2026-11-01T06:00:00</CreDtTm></GrpHdr>
  <Stmt>
   <Id>SYN-2026-10</Id>
   <FrToDt><FrDtTm>2026-10-01T00:00:00</FrDtTm><ToDtTm>2026-10-31T23:59:59</ToDtTm></FrToDt>
   <Acct><Id><Othr><Id>0110012345678</Id></Othr></Id><Ccy>KES</Ccy></Acct>
   <Bal><Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp><Amt Ccy="KES">100000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Dt><Dt>2026-10-01</Dt></Dt></Bal>
   <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp><Amt Ccy="KES">112500.50</Amt><CdtDbtInd>CRDT</CdtDbtInd><Dt><Dt>2026-10-31</Dt></Dt></Bal>
   <Ntry>
    <Amt Ccy="KES">20000.50</Amt><CdtDbtInd>CRDT</CdtDbtInd><Sts>BOOK</Sts>
    <BookgDt><Dt>2026-10-05</Dt></BookgDt><ValDt><Dt>2026-10-05</Dt></ValDt><AcctSvcrRef>BNK-001</AcctSvcrRef>
    <NtryDtls><TxDtls><Refs><EndToEndId>INV-2026-0042</EndToEndId></Refs>
     <RltdPties><Dbtr><Nm>Synthetic Retail Ltd</Nm></Dbtr></RltdPties>
     <RmtInf><Ustrd>Payment for INV-2026-0042</Ustrd></RmtInf></TxDtls></NtryDtls>
   </Ntry>
   <Ntry>
    <Amt Ccy="KES">7500.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts>BOOK</Sts>
    <BookgDt><Dt>2026-10-20</Dt></BookgDt><AcctSvcrRef>BNK-002</AcctSvcrRef>
    <NtryDtls><TxDtls><Refs><EndToEndId>NOTPROVIDED</EndToEndId></Refs>
     <RltdPties><Cdtr><Nm>Synthetic Packaging Co</Nm></Cdtr></RltdPties></TxDtls></NtryDtls>
   </Ntry>
   <Ntry>
    <Amt Ccy="KES">999.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Sts>PDNG</Sts>
    <BookgDt><Dt>2026-10-31</Dt></BookgDt>
   </Ntry>
  </Stmt>
 </BkToCstmrStmt>
</Document>
"""

MT940 = b""":20:STMT2610
:25:0110012345678
:28C:00042/001
:60F:C261001KES100000,00
:61:2610051005C20000,50NTRFINV-2026-0042//BNK-001
:86:Payment for INV-2026-0042
Synthetic Retail Ltd
:61:2610201020D7500,00NCHKNONREF//BNK-002
:86:Synthetic Packaging Co
:62F:C261031KES112500,50
-
"""

OFX = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102

<OFX>
<BANKMSGSRSV1><STMTTRNRS><STMTRS>
<CURDEF>KES
<BANKACCTFROM><BANKID>01<ACCTID>0110012345678<ACCTTYPE>CHECKING</BANKACCTFROM>
<BANKTRANLIST><DTSTART>20261001<DTEND>20261031
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20261005120000<TRNAMT>20000.50<FITID>BNK-001<NAME>Synthetic Retail Ltd<MEMO>INV-2026-0042
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20261020<TRNAMT>-7500.00<FITID>BNK-002<NAME>Synthetic Packaging Co
</BANKTRANLIST>
<LEDGERBAL><BALAMT>112500.50<DTASOF>20261031</LEDGERBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1>
</OFX>
"""

# Newest first, separate debit/credit columns, running balance, thousands separators.
CSV = b"""Synthetic Bank Ltd - Account Statement
Account,0110012345678
Transaction Date,Value Date,Description,Reference,Debit,Credit,Balance
20/10/2026,20/10/2026,Synthetic Packaging Co,BNK-002,"7,500.00",,"112,500.50"
05/10/2026,05/10/2026,Payment for INV-2026-0042,INV-2026-0042,,"20,000.50","120,000.50"
"""


@pytest.mark.parametrize("fmt,data", [("CAMT053", CAMT053), ("MT940", MT940), ("OFX", OFX), ("CSV", CSV)])
def test_every_format_yields_the_same_balanced_statement(fmt, data):
    s = parse_statement(fmt, data)
    assert s.opening_balance == Decimal("100000.00") and s.closing_balance == Decimal("112500.50")
    credits, debits = s.totals()
    assert (credits, debits) == (Decimal("20000.50"), Decimal("7500.00"))
    assert s.opening_balance + credits - debits == s.closing_balance
    assert [(l["transaction_date"], l["debit_credit_indicator"], l["amount"]) for l in s.lines] == [
        (date(2026, 10, 5), "C", 20000.5), (date(2026, 10, 20), "D", 7500.0)]
    # camt/OFX state the period, MT940 dates its balances; CSV only has transaction dates.
    if fmt == "CSV":
        assert (s.period_start, s.period_end) == (date(2026, 10, 5), date(2026, 10, 20))
    else:
        assert (s.period_start, s.period_end) == (date(2026, 10, 1), date(2026, 10, 31))


def test_camt_details_pending_entries_and_counterparties():
    s = parse_statement("CAMT053", CAMT053)
    assert s.account == "0110012345678" and s.currency == "KES"
    credit, debit = s.lines
    assert credit["external_reference"] == "INV-2026-0042" and credit["counterparty_name"] == "Synthetic Retail Ltd"
    assert credit["bank_reference"] == "BNK-001" and credit["narration"] == "Payment for INV-2026-0042"
    assert debit["external_reference"] is None and debit["counterparty_name"] == "Synthetic Packaging Co"
    assert len(s.lines) == 2  # PDNG entry skipped


def test_mt940_fields():
    s = parse_statement("MT940", MT940)
    assert s.account == "0110012345678" and s.currency == "KES" and s.statement_date == date(2026, 10, 31)
    assert s.lines[0]["external_reference"] == "INV-2026-0042" and s.lines[0]["bank_reference"] == "BNK-001"
    assert "Synthetic Retail Ltd" in s.lines[0]["narration"]
    assert s.lines[1]["external_reference"] is None  # NONREF


def test_rejections():
    xxe = b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY x SYSTEM "file:///etc/passwd">]><Document>&x;</Document>'
    with pytest.raises(StatementParseError, match="DOCTYPE"):
        parse_statement("CAMT053", xxe)
    with pytest.raises(StatementParseError, match="Unsupported format"):
        parse_statement("PDF", b"x")
    with pytest.raises(StatementParseError, match="5 MB"):
        parse_statement("CSV", b"x" * (5 * 1024 * 1024 + 1))
    with pytest.raises(StatementParseError, match="Debit and Credit"):
        parse_statement("CSV", b"Date,Description\n2026-10-01,x\n")
    with pytest.raises(StatementParseError, match="several MT940"):
        parse_statement("MT940", MT940 + MT940)
    with pytest.raises(StatementParseError, match="no booked"):
        parse_statement("CSV", b"Date,Amount\n")
