#!/usr/bin/env node
// Launcher for the bundled Python `irwhois` package (stdlib only, no pip needed).
// Finds a Python 3 interpreter and runs `python -m irwhois` with the bundled
// sources on PYTHONPATH, forwarding stdio/args/exit code transparently.
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const PYTHON_DIR = path.join(__dirname, "..", "python");
const CANDIDATES = [["python3"], ["python"], ["py", "-3"]];

function findPython() {
  for (const [cmd, ...prefix] of CANDIDATES) {
    try {
      const r = spawnSync(cmd, [...prefix, "--version"], { stdio: "pipe" });
      if (r.status === 0) return { cmd, prefix };
    } catch {
      // try next candidate
    }
  }
  return null;
}

const found = findPython();
if (!found) {
  console.error(
    "irwhois needs Python 3.8+ on PATH (python3 or python). " +
      "Install it from https://www.python.org/downloads/ and retry."
  );
  process.exit(1);
}

const env = {
  ...process.env,
  PYTHONPATH: PYTHON_DIR + path.delimiter + (process.env.PYTHONPATH || ""),
};

const child = spawnSync(
  found.cmd,
  [...found.prefix, "-m", "irwhois", ...process.argv.slice(2)],
  { stdio: "inherit", env }
);

process.exit(child.status === null ? 1 : child.status);
