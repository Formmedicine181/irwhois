// prepack: stage the Python sources + docs into this folder so the
// published tarball is self-contained. Generated files are gitignored.
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..", "..");
const DEST = path.join(__dirname, ".."); // npm/

function copyDir(src, dst) {
  fs.rmSync(dst, { recursive: true, force: true });
  fs.mkdirSync(dst, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (entry.name === "__pycache__") continue;
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

// 1. Python package -> ./python/irwhois
copyDir(path.join(ROOT, "irwhois"), path.join(DEST, "python", "irwhois"));

// 2. Docs -> ./README.md, ./LICENSE (npm renders these on the package page)
for (const f of ["README.md", "LICENSE"]) {
  fs.copyFileSync(path.join(ROOT, f), path.join(DEST, f));
}

console.log("staged npm payload: python/irwhois, README.md, LICENSE");
