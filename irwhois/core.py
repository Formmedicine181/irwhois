#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure logic for checking .ir domain availability via whois.nic.ir.

This module has zero UI dependencies: no CLI parsing, no printing, no colors,
no web server, no HTML. It takes data in and returns plain result dicts.

Result statuses (``status`` field):
    free      available for registration
    taken     already registered / taken
    reserved  reserved / not registrable (e.g. names shorter than 3 chars)
    invalid   invalid input (not a .ir domain)
    error     whois server communication failure
"""

import html as htmlmod
import re
import socket
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

WHOIS_HOST = "whois.nic.ir"
WHOIS_PORT = 43
WHOIS_HTTP_URL = "https://whois.nic.ir/WHOIS?name="
DEFAULT_TIMEOUT = 12
DEFAULT_WORKERS = 4
DEFAULT_DELAY = 0.4


# ---------------------------------------------------------------------------
# Input normalization (domain / site URL / whois URL)
# ---------------------------------------------------------------------------

def normalize_domain(raw: str) -> str:
    """Normalize any input (domain, site URL, whois.nic.ir link) to a clean domain."""
    if raw is None:
        return ""
    s = raw.strip().strip('"').strip("'").strip()
    if not s:
        return ""
    # Strip invisible direction marks (ZWNJ \u200c is kept: it is part of the domain)
    s = s.replace("\u200f", "").replace("\u200e", "").replace("\ufeff", "")
    s = s.strip()
    low = s.lower()

    # 1) whois link such as https://whois.nic.ir/WHOIS?name=example.ir
    if "whois.nic.ir" in low and "name=" in s:
        try:
            qs = urllib.parse.urlparse(s).query
            params = urllib.parse.parse_qs(qs)
            if "name" in params and params["name"]:
                s = params["name"][0].strip()
            else:
                m = re.search(r"name=([^&\s]+)", s, re.I)
                if m:
                    s = urllib.parse.unquote(m.group(1)).strip()
        except Exception:
            pass
        low = s.lower()

    # 2) Full site URL such as https://example.ir/path?q=1
    if "://" in s:
        try:
            p = urllib.parse.urlparse(s if "://" in s else "http://" + s)
            if p.hostname:
                s = p.hostname.strip()
            else:
                s = p.path.split("/")[0].strip()
        except Exception:
            pass
    else:
        # Domain with a path suffix: example.ir/foo
        s = s.split("/")[0].split("?")[0].split("#")[0].strip()
        # Strip port: example.ir:8080
        if re.match(r"^[^:]+:\d+$", s):
            s = s.split(":")[0]

    s = s.strip().lower().rstrip(".").strip()
    # A leading www. is dropped: its whois record is misleading, while users
    # pasting a site link almost always mean the apex domain.
    if s.startswith("www."):
        s = s[4:]

    # Bare name without a dot → assume .ir
    if s and "." not in s:
        s += ".ir"
    # Drop inner whitespace
    s = re.sub(r"\s+", "", s)
    return s


def is_valid_ir_domain(domain: str) -> bool:
    """Accept Latin alphanumerics, hyphens and Persian (IDN) letters under .ir."""
    if not domain or len(domain) < 4:
        return False
    if not domain.endswith(".ir"):
        return False
    if ".." in domain or " " in domain or "/" in domain:
        return False
    if not re.match(r"^[a-z0-9\u0600-\u06FF\u0750-\u077F\.\-]+$", domain, re.I):
        return False
    return True


def sld_label(domain: str) -> str:
    """Main name part (first label); e.g. fa in fa.ir, shop in shop.co.ir."""
    return (domain or "").split(".")[0]


# ---------------------------------------------------------------------------
# WHOIS queries
# ---------------------------------------------------------------------------

def query_socket(domain: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Query the whois server directly over port 43."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((WHOIS_HOST, WHOIS_PORT))
        s.sendall((domain + "\r\n").encode("utf-8"))
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
        return b"".join(chunks).decode("utf-8", errors="replace")
    finally:
        try:
            s.close()
        except Exception:
            pass


class ReservedDomainError(ValueError):
    """Domain is not registrable per registry rules (too short / Bad query)."""
    pass


def query_http(domain: str, timeout: int = DEFAULT_TIMEOUT + 5) -> str:
    """Scrape the whois.nic.ir web page and extract the <pre> answer.

    Raises ReservedDomainError on «Bad query / invalid request» (e.g. 1–2
    character domains) so they are never misreported as «free».
    """
    url = WHOIS_HTTP_URL + urllib.parse.quote(domain)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; IR-Domain-Checker/1.0)",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw_html = resp.read().decode("utf-8", errors="replace")
    if re.search(r"Bad query|پرسش\s*نامعتبر|bad-thing", raw_html, re.I):
        raise ReservedDomainError(
            "پاسخ سرور: پرسش نامعتبر (این نام طبق قوانین ایرنیک قابل ثبت نیست — مثلاً کمتر از ۳ حرف)"
        )
    m = re.search(r"<pre[^>]*>(.*?)</pre>", raw_html, re.S | re.I)
    if not m:
        raise RuntimeError("پاسخ HTTP قابل تجزیه نبود (تگ <pre> پیدا نشد)")
    text = re.sub(r"<br\s*/?>", "\n", m.group(1), flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return htmlmod.unescape(text)


def classify_whois_text(text: str) -> tuple:
    """Map raw whois text to (status, available).

    - free:  «no entries found» / ERROR:101 → available for registration
    - taken: contains a «domain:» line → already registered
    """
    low = (text or "").lower()
    if "no entries found" in low or "error:101" in low:
        return "free", True
    if re.search(r"^\s*domain\s*:", text or "", re.M | re.I):
        return "taken", False
    if "not available for registration" in low:
        return "taken", False
    return "error", False


# ---------------------------------------------------------------------------
# Main logic API
# ---------------------------------------------------------------------------

def check_domain(raw_input: str, timeout: int = DEFAULT_TIMEOUT,
                 method: str = "auto", retries: int = 1) -> dict:
    """Check a single domain. Returns a standard result dict.

    Statuses: free | taken | reserved | invalid | error.
    """
    domain = normalize_domain(raw_input)
    result = {
        "input": (raw_input or "").strip(),
        "domain": domain,
        "status": "invalid",   # free | taken | reserved | invalid | error
        "available": False,
        "label_fa": "",
        "raw": "",
        "method_used": method,
        "error": "",
        "whois_url": "",
    }
    if not is_valid_ir_domain(domain):
        result["error"] = "دامنه معتبر .ir نیست"
        result["label_fa"] = "نامعتبر"
        return result

    # Official IRNIC rule: domain names must be 3–63 characters long.
    # Port-43 whois wrongly answers «no entries found» for 1–2 char names
    # while the web page says «Bad query» — and such names are not registrable.
    # So short names are reported as reserved before any query. (e.g. fa.ir)
    if len(sld_label(domain)) < 3:
        result["status"] = "reserved"
        result["label_fa"] = "رزرو/غیرقابل ثبت 🔒"
        result["error"] = "طبق قوانین ایرنیک نام دامنه باید حداقل ۳ حرف باشد؛ این نام قابل ثبت نیست"
        result["whois_url"] = WHOIS_HTTP_URL + urllib.parse.quote(domain)
        result["method_used"] = "rule"
        return result

    result["whois_url"] = WHOIS_HTTP_URL + urllib.parse.quote(domain)
    # HTTP first: more stable and detects «Bad query»; socket is the fallback.
    methods = ["http", "socket"] if method == "auto" else [method]
    last_err = ""
    for m in methods:
        for attempt in range(retries + 1):
            try:
                text = query_socket(domain, timeout) if m == "socket" else query_http(domain, timeout)
                status, avail = classify_whois_text(text)
                result["status"] = status
                result["available"] = avail
                result["raw"] = text.strip()
                result["method_used"] = m
                if status == "free":
                    result["label_fa"] = "آزاد ✅ (قابل ثبت)"
                elif status == "taken":
                    result["label_fa"] = "اشغال ❌ (ثبت شده)"
                else:
                    result["label_fa"] = "نامشخص ⚠️"
                    result["error"] = "پاسخ سرور نامشخص بود"
                return result
            except ReservedDomainError as e:
                result["status"] = "reserved"
                result["label_fa"] = "رزرو/غیرقابل ثبت 🔒"
                result["error"] = str(e)
                result["method_used"] = m
                return result
            except Exception as e:
                last_err = f"{m}: {e}"
                time.sleep(0.5)
    result["status"] = "error"
    result["label_fa"] = "خطا ⚠️"
    result["error"] = last_err or "ارتباط با whois.nic.ir برقرار نشد (اتصال اینترنت/VPN را بررسی کنید)"
    return result


def batch_check(domains, workers: int = DEFAULT_WORKERS, delay: float = DEFAULT_DELAY,
                timeout: int = DEFAULT_TIMEOUT, method: str = "auto",
                on_progress=None) -> list:
    """Check a list of domains concurrently, preserving input order."""
    # De-duplicate while preserving order
    seen, unique = set(), []
    for d in domains:
        key = normalize_domain(d)
        if key and key not in seen:
            seen.add(key)
            unique.append(d)
        elif not key and d.strip():
            unique.append(d)

    results = [None] * len(unique)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        fut_map = {ex.submit(check_domain, d, timeout, method): i for i, d in enumerate(unique)}
        done = 0
        for fut in as_completed(fut_map):
            i = fut_map[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = {"input": unique[i], "domain": normalize_domain(unique[i]),
                              "status": "error", "available": False, "label_fa": "خطا ⚠️",
                              "raw": "", "method_used": method, "error": str(e), "whois_url": ""}
            done += 1
            if on_progress:
                try:
                    on_progress(done, len(unique), results[i])
                except Exception:
                    pass
            if delay and done < len(unique):
                time.sleep(delay / max(1, workers))
    return results
