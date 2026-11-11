"""Network label printing: ZPL/TSPL rendering, private-network guard and raw TCP delivery."""
import asyncio
from datetime import date

import pytest

from app.services import label_printer_service as lp


class FakePrinter:
    """Minimal raw-TCP (port 9100 style) printer that records what it receives."""

    def __init__(self):
        self.received = bytearray()
        self.server = None

    async def _handle(self, reader, writer):
        self.received += await reader.read()
        writer.close()

    async def __aenter__(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        self.server.close()
        await self.server.wait_closed()


def _labels():
    return [lp.lot_label("06123456789012", "LOT42", "(01)06123456789012(10)LOT42(17)271231", date(2027, 12, 31), None, 3),
            lp.sscc_label("106141411234567897", "PAL-1", "SHIP-9", 1)]


def test_zpl_uses_gs1_128_mode_d_and_copies():
    out = lp.render(lp.PrinterSpec("ZPL", 203, 100, 150), _labels()).decode()
    assert out.count("^XA") == 2 and out.count("^XZ") == 2
    assert "^BCN,160,Y,N,N,D^FD(01)06123456789012(10)LOT42(17)271231^FS" in out
    assert "^FD(00)106141411234567897^FS" in out and "^PQ3" in out and "^PW799" in out
    assert "EXP 2027-12-31" in out


def test_tspl_uses_ean128_and_strips_command_characters_from_captions():
    label = lp.LabelContent("(01)06123456789012(10)LOTX", 'Bad "title" ^XA', ("x",), 2)
    out = lp.render(lp.PrinterSpec("TSPL", 300, 60, 40), [label]).decode()
    assert 'BARCODE 40,' in out and '"EAN128"' in out and "PRINT 1,2" in out
    assert "^XA" not in out and '"title"' not in out and '"(01)06123456789012(10)LOTX"' in out


def test_barcode_data_is_never_altered_or_truncated():
    with pytest.raises(lp.PrinterError, match="cannot be printed"):
        lp.render(lp.PrinterSpec("ZPL"), [lp.LabelContent('(01)06123456789012(10)LOT"^~X', "t")])
    with pytest.raises(lp.PrinterError, match="cannot be printed"):
        lp.render(lp.PrinterSpec("ZPL"), [lp.LabelContent("(01)06123456789012(10)LOTé", "t")])
    long_ai = "(01)06123456789012(10)" + "L" * 20 + "(17)271231(21)" + "S" * 10
    with pytest.raises(lp.PrinterError, match="limit is 48"):
        lp.render(lp.PrinterSpec("ZPL"), [lp.LabelContent(long_ai, "t")])
    exact = "(01)06123456789012(10)" + "L" * 20 + "(17)271231"  # 42 encoded chars
    assert exact in lp.render(lp.PrinterSpec("ZPL"), [lp.LabelContent(exact, "t")]).decode()


def test_unknown_protocol_and_empty_job_rejected():
    with pytest.raises(lp.PrinterError, match="protocol"):
        lp.render(lp.PrinterSpec("EPL"), _labels())
    with pytest.raises(lp.PrinterError, match="Nothing"):
        lp.render(lp.PrinterSpec("ZPL"), [])


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["8.8.8.8", "169.254.169.254", "0.0.0.0", "224.0.0.1", "::ffff:169.254.169.254",
                                  "::ffff:8.8.8.8", "2001:0:4136:e378::1", "100.64.0.1", "a" * 64 + ".local", "", ".."])
async def test_public_metadata_special_and_malformed_hosts_are_refused(host):
    with pytest.raises(lp.PrinterError):
        await lp.resolve_printer_addresses(host)


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["127.0.0.1", "10.20.0.15", "192.168.1.50", "172.16.4.4", "::1"])
async def test_private_addresses_are_allowed(host):
    assert await lp.resolve_printer_addresses(host)


@pytest.mark.asyncio
async def test_send_raw_delivers_bytes_and_reports_connection_failures():
    payload = lp.render(lp.PrinterSpec("ZPL"), _labels())
    async with FakePrinter() as printer:
        await lp.send_raw("127.0.0.1", printer.port, payload)
        for _ in range(50):
            if len(printer.received) == len(payload):
                break
            await asyncio.sleep(0.02)
    assert bytes(printer.received) == payload
    with pytest.raises(lp.PrinterError, match="Cannot connect"):
        await lp.send_raw("127.0.0.1", printer.port, payload)  # server closed
