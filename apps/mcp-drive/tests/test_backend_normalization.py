"""Regression: nomes do Drive vem em NFC ou NFD; normalizar pra NFC sempre."""

import unicodedata

from mcp_drive.backend import _to_node


def test_nfd_name_normalized_to_nfc() -> None:
    nfd_name = "DEFINI" + "C" + "̧" + "O" + "̃" + "ES"
    assert unicodedata.is_normalized("NFD", nfd_name)
    assert not unicodedata.is_normalized("NFC", nfd_name)

    payload = {
        "id": "abc",
        "name": nfd_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    node = _to_node(payload)

    assert node.name == "DEFINIÇÕES"
    assert unicodedata.is_normalized("NFC", node.name)


def test_nfc_name_passes_through() -> None:
    payload = {"id": "abc", "name": "DEFINIÇÕES", "mimeType": "x"}
    node = _to_node(payload)
    assert node.name == "DEFINIÇÕES"
