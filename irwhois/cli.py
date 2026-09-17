#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command-line and interactive interface for checking .ir domains.

CLI layer only: argument parsing, input-file reading, colored printing and
CSV export. All domain logic lives in irwhois.core; the web UI (irwhois.web)
is imported lazily, only when --web is used, so this module has no hard
dependency on the web layer.

Run:
    python -m irwhois example.ir
    python -m irwhois -f domains.txt -o result.csv
    python -m irwhois -i
"""

import argparse
import csv
import re
import sys

from irwhois import __version__
from irwhois.core import (
    DEFAULT_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    batch_check,
    check_domain,
)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# File input/output
# ---------------------------------------------------------------------------

def read_domains_from_file(path: str) -> list:
    """Read domains from a txt or csv file (one per line / first .ir column)."""
    domains = []
    with open(path, encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        if path.lower().endswith(".csv") or "," in sample.splitlines()[0] if sample.splitlines() else False:
            try:
                reader = csv.reader(f)
                for row in reader:
                    for cell in row:
                        cell = (cell or "").strip()
                        if not cell:
                            continue
                        # A cell that looks like a domain/link
                        if ".ir" in cell.lower() or "whois.nic.ir" in cell.lower() or "://" in cell:
                            domains.append(cell)
                            break
                return domains
            except Exception:
                f.seek(0)
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Support multi-domain lines separated by , ; | space
            parts = re.split(r"[,;\s|]+", line)
            for p in parts:
                if p.strip():
                    domains.append(p.strip())
    return domains


def save_csv(results: list, path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["input", "domain", "status", "available", "label_fa", "whois_url", "error"])
        for r in results:
            w.writerow([r.get("input", ""), r.get("domain", ""), r.get("status", ""),
                        "yes" if r.get("available") else "no",
                        r.get("label_fa", ""), r.get("whois_url", ""), r.get("error", "")])


# ---------------------------------------------------------------------------
# Terminal rendering
# ---------------------------------------------------------------------------

def colorize(result: dict, no_color: bool = False) -> str:
    st = result["status"]
    label = result["label_fa"] or st
    if no_color:
        return f'{result["domain"]} -> {label}'
    if st == "free":
        return f'{GREEN}{BOLD}{result["domain"]} -> {label}{RESET}'
    if st == "taken":
        return f'{RED}{result["domain"]} -> {label}{RESET}'
    if st == "invalid":
        return f'{YELLOW}{result["domain"]} -> نامعتبر ({result.get("error","")}){RESET}'
    if st == "reserved":
        return f'{CYAN}{result["domain"]} -> {label} ({result.get("error","")}){RESET}'
    return f'{YELLOW}{result["domain"]} -> خطا ({result.get("error","")}){RESET}'


def print_summary(results: list):
    free = sum(1 for r in results if r["status"] == "free")
    taken = sum(1 for r in results if r["status"] == "taken")
    reserved = sum(1 for r in results if r["status"] == "reserved")
    err = len(results) - free - taken - reserved
    print(f"\n{BOLD}— جمع‌بندی: {len(results)} دامنه | {GREEN}آزاد: {free}{RESET} | "
          f"{RED}اشغال: {taken}{RESET} | {CYAN}رزرو: {reserved}{RESET} | "
          f"{YELLOW}خطا/نامعتبر: {err}{RESET}")


# ---------------------------------------------------------------------------
# Interactive terminal mode (Persian)
# ---------------------------------------------------------------------------

def interactive_mode(args):
    # Lazy import so the CLI works without the web layer
    from irwhois.web import run_web

    print(f"{BOLD}{CYAN}=== بررسی دامنه .ir (whois.nic.ir) ==={RESET}")
    print("ورودی می‌تواند دامنه (example.ir)، لینک سایت یا لینک whois باشد.")
    print("دستورها: exit خروج | web اجرای رابط وب\n")
    while True:
        try:
            choice = input(f"{BOLD}انتخاب [1] تکی  [2] گروهی  [3] فایل  [q] خروج: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nخدانگهدار!")
            break
        if choice.lower() in ("q", "quit", "exit", "خروج"):
            break
        if choice == "web":
            run_web(args.port)
            continue
        if choice == "1":
            raw = input("دامنه یا لینک را وارد کنید: ").strip()
            if not raw:
                continue
            r = check_domain(raw, args.timeout, args.method)
            print(colorize(r, args.no_color))
            if r.get("raw"):
                print(f"--- پاسخ whois ---\n{r['raw'][:1500]}")
            print(f"لینک استعلام: {r.get('whois_url','-')}\n")
        elif choice == "2":
            print("دامنه‌ها را وارد کنید (هر خط یکی، خط خالی = پایان):")
            lines = []
            while True:
                try:
                    line = input()
                except (EOFError, KeyboardInterrupt):
                    break
                if not line.strip():
                    break
                lines += re.split(r"[,;\s|]+", line.strip())
            lines = [x for x in lines if x.strip()]
            if not lines:
                print("ورودی خالی بود.\n")
                continue
            results = batch_check(lines, args.workers, args.delay, args.timeout, args.method,
                                  on_progress=lambda d, t, r: print(f"  [{d}/{t}] " + colorize(r, args.no_color)))
            print_summary(results)
            if args.output:
                save_csv(results, args.output)
                print(f"ذخیره شد: {args.output}\n")
        elif choice == "3":
            path = input("مسیر فایل txt/csv: ").strip().strip('"')
            try:
                domains = read_domains_from_file(path)
            except Exception as e:
                print(f"خطا در خواندن فایل: {e}\n")
                continue
            print(f"{len(domains)} دامنه پیدا شد. در حال بررسی...")
            results = batch_check(domains, args.workers, args.delay, args.timeout, args.method,
                                  on_progress=lambda d, t, r: print(f"  [{d}/{t}] " + colorize(r, args.no_color)))
            print_summary(results)
            out = input("مسیر ذخیره CSV (خالی = عدم ذخیره): ").strip()
            if out:
                save_csv(results, out)
                print(f"ذخیره شد: {out}\n")
        else:
            print("گزینه نامعتبر.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="irwhois",
        description="Check .ir domain availability via whois.nic.ir (single & batch)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("domains", nargs="*", help="domain or link (e.g. example.ir or https://whois.nic.ir/WHOIS?name=example.ir)")
    p.add_argument("-f", "--file", help="input txt/csv file with domains (one per line)")
    p.add_argument("-o", "--output", help="save results to CSV")
    p.add_argument("--web", action="store_true", help="launch the Persian web UI")
    p.add_argument("--port", type=int, default=8000, help="web UI port (default: 8000)")
    p.add_argument("--host", default="127.0.0.1", help="web UI bind address (use 0.0.0.0 inside Docker)")
    p.add_argument("-i", "--interactive", action="store_true", help="Persian interactive mode")
    p.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS, help=f"parallel workers (default: {DEFAULT_WORKERS})")
    p.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="delay between queries (seconds)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-query timeout (seconds)")
    p.add_argument("--method", choices=["auto", "socket", "http"], default="auto", help="query method (default: auto)")
    p.add_argument("--retries", type=int, default=1, help="retries on failure")
    p.add_argument("--show-raw", action="store_true", help="print raw whois text")
    p.add_argument("--no-color", action="store_true", help="disable colors")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.web:
        from irwhois.web import run_web
        run_web(args.port, args.timeout, args.method, args.workers, args.host)
        return

    # Collect inputs
    inputs = list(args.domains or [])
    if args.file:
        try:
            inputs += read_domains_from_file(args.file)
        except FileNotFoundError:
            print(f"فایل پیدا نشد: {args.file}", file=sys.stderr)
            sys.exit(1)

    if args.interactive or (not inputs and sys.stdin.isatty()):
        # No input given → interactive mode
        if not inputs:
            interactive_mode(args)
            return

    if not inputs and not sys.stdin.isatty():
        # Pipe support: cat domains.txt | irwhois -o result.csv
        inputs = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]

    if not inputs:
        build_parser().print_help()
        print("\nExamples:\n  irwhois example.ir\n  irwhois -f domains.txt -o result.csv\n  irwhois --web")
        return

    # Split multi-domain arguments
    flat = []
    for item in inputs:
        flat += [x for x in re.split(r"[,;\s|]+", item) if x.strip()]
    inputs = flat

    if len(inputs) == 1:
        r = check_domain(inputs[0], args.timeout, args.method, args.retries)
        print(colorize(r, args.no_color))
        print(f"لینک استعلام: {r.get('whois_url','-')}")
        if args.show_raw and r.get("raw"):
            print(f"--- پاسخ خام ---\n{r['raw']}")
        if r["status"] == "invalid":
            print(f"خطا: {r['error']}", file=sys.stderr)
        results = [r]
    else:
        print(f"در حال بررسی {len(inputs)} دامنه با {args.workers} نخ موازی...\n")
        results = batch_check(
            inputs, args.workers, args.delay, args.timeout, args.method,
            on_progress=lambda d, t, r: print(f"  [{d}/{t}] " + colorize(r, args.no_color)),
        )
        print_summary(results)
        if args.show_raw:
            for r in results:
                print(f"\n===== {r['domain']} ({r['label_fa']}) =====\n{(r.get('raw') or r.get('error',''))[:2000]}")

    if args.output:
        save_csv(results, args.output)
        print(f"\n✅ نتایج در {args.output} ذخیره شد.")


if __name__ == "__main__":
    main()
