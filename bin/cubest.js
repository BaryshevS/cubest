#!/usr/bin/env node
// Thin npm wrapper — delegates to python3 cubest.py located next to this file.
// Requires Python 3.8+ available on PATH. Optional: pip install pyyaml.

const { spawn } = require("child_process");
const path = require("path");

const script = path.resolve(__dirname, "..", "cubest.py");
const py = process.env.PYTHON || "python3";

const child = spawn(py, [script, ...process.argv.slice(2)], {
  stdio: "inherit",
});

child.on("error", (err) => {
  if (err.code === "ENOENT") {
    console.error(
      `cubest: '${py}' not found. Install Python 3.8+ or set PYTHON env var.`
    );
    process.exit(127);
  }
  console.error("cubest: failed to spawn:", err.message);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  process.exit(code ?? (signal ? 1 : 0));
});
