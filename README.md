# irwhois

Check **.ir domain availability** with live queries to `whois.nic.ir` — single or batch, from the terminal or a web UI.

- ✅ Zero dependencies (Python 3.8+ standard library only)
- ✅ Accepts a bare domain, a site URL, or a whois link such as `https://whois.nic.ir/WHOIS?name=example.ir`
- ✅ Single + batch checks (txt/csv files, pipes, web UI)
- ✅ Persian (RTL) web UI with CSV export
- ✅ Robust detection: HTTP first, port-43 whois fallback, `Bad query` and minimum-length rules handled

## Install

```bash
pip install .
# then use the `irwhois` command from anywhere
```

Or run without installing, from the project root:

```bash
python -m irwhois example.ir
```

## Usage

```bash
# Single domain (or link)
irwhois example.ir
irwhois "https://whois.nic.ir/WHOIS?name=example.ir"
irwhois google.ir myshop.ir --show-raw

# Batch from file
irwhois -f domains_sample.txt -o result.csv

# Pipe
cat domains_sample.txt | irwhois -o result.csv

# Interactive mode (Persian)
irwhois -i

# Web UI (Persian, RTL)
irwhois --web
# open http://127.0.0.1:8000
```

As a library:

```python
from irwhois import check_domain, batch_check

print(check_domain("example.ir")["status"])   # taken | free | reserved | ...
print(batch_check(["a.ir", "b.ir"]))
```

## How availability is detected

| Server answer | Status |
|---|---|
| `ERROR:101: no entries found` | **free ✅** (available) |
| Contains a `domain:` line | **taken ❌** (registered) |
| `Bad query` / name shorter than 3 chars (e.g. `fa.ir`) | **reserved 🔒** (not registrable) |

Per official [IRNIC domain rules](https://www.nic.ir/Terms_and_Conditions_ir,_Appendix_1_Domain_Rules), names must be 3–63 characters. Port-43 whois wrongly answers “no entries found” for 1–2 character names while the web page returns “Bad query”, so short names are reported as reserved instead of free.

## Web UI & API

- Single check + batch check (textarea, txt/csv upload, search, status filter, CSV download, copy-free-domains)
- Internal API:
  - `GET /api/check?domain=example.ir`
  - `POST /api/batch` with body `{"domains": ["a.ir", "b.ir"]}`

## Options

```
-w / --workers   parallel workers (default: 4)
--delay          delay between queries in seconds (default: 0.4)
--timeout        per-query timeout in seconds (default: 12)
--method         auto | socket | http (default: auto)
--show-raw       print raw whois text
-o / --output    save results to CSV
--version        print version
```

> Tip: for heavy batch runs, lower the workers (e.g. 2–3) and raise the delay so your IP doesn't get rate-limited.

## Project layout

```
irwhois/
  core.py    pure logic: normalize, validate, query, classify (no UI)
  cli.py     command-line + interactive interface
  web.py     web server + API (uses only core)
  web/       frontend: index.html / styles.css / app.js
```

Dependency rules: `core` depends on nothing UI-related, `web` depends only on `core`, and `cli` loads `web` lazily (only for `--web`).

## راهنمای فارسی

ورودی می‌تواند دامنه (`example.ir`)، لینک سایت (`https://myshop.ir`) یا لینک whois (`https://whois.nic.ir/WHOIS?name=myshop.ir`) باشد؛ هم تکی و هم گروهی پشتیبانی می‌شود. برای استفاده راحت، `irwhois --web` را اجرا کنید و در مرورگر `http://127.0.0.1:8000` را باز کنید.

## License

MIT — see [LICENSE](LICENSE).
