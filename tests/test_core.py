"""Offline unit tests for irwhois.core (no network access)."""

import irwhois
from irwhois import core
from irwhois.core import (
    batch_check,
    check_domain,
    classify_whois_text,
    is_valid_ir_domain,
    normalize_domain,
    sld_label,
)


def test_normalize_plain_domain():
    assert normalize_domain("Example.IR") == "example.ir"
    assert normalize_domain("  myshop.ir  ") == "myshop.ir"


def test_normalize_bare_name_gets_ir():
    assert normalize_domain("myshop") == "myshop.ir"


def test_normalize_site_url():
    assert normalize_domain("https://myshop.ir/path?q=1") == "myshop.ir"
    assert normalize_domain("http://www.myshop.ir/") == "myshop.ir"


def test_normalize_whois_link():
    assert normalize_domain("https://whois.nic.ir/WHOIS?name=example.ir") == "example.ir"


def test_normalize_strips_port_and_path():
    assert normalize_domain("example.ir:8080") == "example.ir"
    assert normalize_domain("example.ir/foo") == "example.ir"


def test_is_valid_ir_domain():
    assert is_valid_ir_domain("example.ir")
    assert is_valid_ir_domain("shop.co.ir")
    assert not is_valid_ir_domain("example.com")
    assert not is_valid_ir_domain("example")
    assert not is_valid_ir_domain("bad domain.ir")
    assert not is_valid_ir_domain("")


def test_sld_label():
    assert sld_label("fa.ir") == "fa"
    assert sld_label("shop.co.ir") == "shop"


def test_classify_free():
    text = "%ERROR:101: no entries found\n% No entries found in the selected source(s)."
    assert classify_whois_text(text) == ("free", True)


def test_classify_taken():
    text = "domain:\t\tgoogle.ir\nremarks:\thidden by holder"
    assert classify_whois_text(text) == ("taken", False)
    assert classify_whois_text("remarks: This domain is not available for registration")[0] == "taken"


def test_classify_unknown():
    assert classify_whois_text("something unexpected")[0] == "error"


def test_short_name_is_reserved_without_network(monkeypatch):
    # Must never touch the network for short names (IRNIC min length = 3).
    def _boom(*a, **k):
        raise AssertionError("network should not be used")

    monkeypatch.setattr(core, "query_http", _boom)
    monkeypatch.setattr(core, "query_socket", _boom)
    r = check_domain("fa.ir")
    assert r["domain"] == "fa.ir"
    assert r["status"] == "reserved"
    assert r["available"] is False
    assert r["method_used"] == "rule"


def test_invalid_input():
    r = check_domain("not a domain!!!")
    assert r["status"] == "invalid"


def test_taken_and_free_via_mocked_http(monkeypatch):
    monkeypatch.setattr(
        core, "query_http",
        lambda domain, timeout=12: "domain:\t\t%s\nsource: IRNIC" % domain,
    )
    assert check_domain("google.ir")["status"] == "taken"
    monkeypatch.setattr(
        core, "query_http",
        lambda domain, timeout=12: "%ERROR:101: no entries found",
    )
    r = check_domain("somebrandnewname12345.ir")
    assert (r["status"], r["available"]) == ("free", True)


def test_batch_dedupes_and_preserves_order(monkeypatch):
    monkeypatch.setattr(
        core, "query_http",
        lambda domain, timeout=12: "%ERROR:101: no entries found",
    )
    results = batch_check(
        ["https://whois.nic.ir/WHOIS?name=aaa123.ir", "aaa123.ir", "bbb123.ir"],
        workers=2,
        delay=0,
    )
    assert [r["domain"] for r in results] == ["aaa123.ir", "bbb123.ir"]
    assert all(r["status"] == "free" for r in results)


def test_package_version():
    assert irwhois.__version__ == "1.0.0"
