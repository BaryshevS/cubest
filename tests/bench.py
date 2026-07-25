#!/usr/bin/env python3
"""Load / perf smoke-tests for cubest.

Not run by default. Two modes:

    # quick sanity — 10k files / 500k records, must fit in seconds
    python3 tests/bench.py

    # heavy — 200k files / 5M records, tune HEAVY=1 (~30 sec, ~500 MiB RSS)
    HEAVY=1 python3 tests/bench.py

Hard-fail thresholds are chosen so a regression is obvious; passing does NOT
prove production behavior at 10 TiB, but confirms that constant factors and
memory footprint stay linear (per-record time < ~2 µs, per-file < ~200 µs,
peak RSS < ~1 KiB per unique cube leaf).
"""

import gzip
import io
import os
import random
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cubest  # noqa: E402
from cubest import OlapCube, Extractor, iter_files, should_scan  # noqa: E402

DYN = str(ROOT / "cubest.py")
HEAVY = bool(os.environ.get("HEAVY"))

N_RECORDS = 5_000_000 if HEAVY else 500_000
N_FILES = 200_000 if HEAVY else 10_000
STREAM_LINES = 5_000_000 if HEAVY else 500_000

MAX_INSERT_SEC = 15.0 if HEAVY else 4.0     # ~130k rec/s on CPython 3.8
MAX_FILE_SCAN_SEC = 60.0 if HEAVY else 8.0
MAX_STREAM_SEC = 45.0 if HEAVY else 15.0    # heavy nginx regex ~40k lines/s
MAX_RSS_KIB = 2_000_000 if HEAVY else 400_000   # rough ceiling
MAX_FORMAT_SEC = 2.0


def _peak_rss_kib() -> int:
    r = resource.getrusage(resource.RUSAGE_SELF)
    # Linux gives KiB; macOS gives bytes.
    if sys.platform == "darwin":
        return r.ru_maxrss // 1024
    return r.ru_maxrss


def _fmt_hz(n, sec):
    if sec <= 0:
        return "∞"
    return f"{n/sec:,.0f}/s"


class InsertPerfTests(unittest.TestCase):
    """Raw cube ingestion — worst-case wide fan-out."""

    def test_insert_records(self):
        rnd = random.Random(0)
        dims = ["kind", "region", "status"]
        cube = OlapCube(dims, [
            {"name": "cnt", "type": "count"},
            {"name": "bytes", "type": "sum", "field": "b"},
            {"name": "avg_lat", "type": "avg", "field": "lat"},
        ])
        kinds = [f"k{i}" for i in range(20)]
        regions = [f"r{i}" for i in range(50)]
        statuses = [200, 301, 404, 500]

        t0 = time.perf_counter()
        for _ in range(N_RECORDS):
            cube.add({
                "kind": rnd.choice(kinds),
                "region": rnd.choice(regions),
                "status": rnd.choice(statuses),
                "b": rnd.randint(100, 5000),
                "lat": rnd.random(),
            })
        dt = time.perf_counter() - t0
        rss = _peak_rss_kib()
        print(f"[insert] {N_RECORDS:,} recs in {dt:.2f}s "
              f"({_fmt_hz(N_RECORDS, dt)}), peak RSS {rss:,}KiB")
        self.assertLess(dt, MAX_INSERT_SEC,
                        f"insert perf regression: {dt:.2f}s > {MAX_INSERT_SEC}s")
        self.assertLess(rss, MAX_RSS_KIB,
                        f"memory regression: {rss}KiB > {MAX_RSS_KIB}KiB")

    def test_format_speed_after_insert(self):
        cube = OlapCube(["a", "b"], [{"name": "n", "type": "count"}])
        for i in range(200_000):
            cube.add({"a": f"g{i % 100}", "b": f"h{i % 500}"})
        t0 = time.perf_counter()
        s = cube.format_flat(top_n=50, min_count=1, max_lines=200)
        dt = time.perf_counter() - t0
        print(f"[format flat] 50k unique cells → {len(s):,} bytes in {dt*1000:.1f}ms")
        self.assertLess(dt, MAX_FORMAT_SEC)


class FileScanPerfTests(unittest.TestCase):
    """Many small files — paths preset with no content read."""

    def test_many_small_files(self):
        td = Path(tempfile.mkdtemp(prefix="dyn_bench_"))
        try:
            # Balanced tree: 100 dirs × N/100 files
            per_dir = max(N_FILES // 100, 1)
            for d in range(100):
                sub = td / f"d{d:03d}"
                sub.mkdir()
                for f in range(per_dir):
                    (sub / f"f{f}.txt").write_bytes(b"")
            file_count = 100 * per_dir

            t0 = time.perf_counter()
            r = subprocess.run(
                ["python3", DYN, "--profile", "file_tree", str(td)],
                capture_output=True, text=True,
            )
            dt = time.perf_counter() - t0
            print(f"[scan] {file_count:,} files (paths preset) in {dt:.2f}s "
                  f"({_fmt_hz(file_count, dt)}), stdout {len(r.stdout):,}B")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertLess(dt, MAX_FILE_SCAN_SEC,
                            f"file-scan regression: {dt:.2f}s > {MAX_FILE_SCAN_SEC}s")
        finally:
            shutil.rmtree(td, ignore_errors=True)


class StreamingPerfTests(unittest.TestCase):
    """Simulate a huge gzip log — memory MUST stay flat regardless of size."""

    def _mk_log(self, path: Path, lines: int):
        # ~150 bytes/line combined format sample
        row = (
            '10.0.0.{ip} - - [10/Jul/2026:00:00:00 +0000] '
            '"GET /api/v1/{seg} HTTP/1.1" {st} 1234 "-" "curl/8" 0.045\n'
        )
        segs = ["users", "orders", "search", "auth", "static", "img"]
        with gzip.open(path, "wt") as fh:
            for i in range(lines):
                fh.write(row.format(
                    ip=(i % 250) + 1,
                    seg=segs[i % len(segs)],
                    st=[200, 301, 404, 500][i % 4],
                ))

    def test_gzip_stream_stays_flat(self):
        td = Path(tempfile.mkdtemp(prefix="dyn_bench_"))
        try:
            gz = td / "access.log.gz"
            self._mk_log(gz, STREAM_LINES)
            sz = gz.stat().st_size
            print(f"[stream] input: {sz/1024/1024:.1f}MiB gzip, "
                  f"{STREAM_LINES:,} lines")

            tracemalloc.start()
            rss_before = _peak_rss_kib()
            t0 = time.perf_counter()
            r = subprocess.run(
                ["python3", DYN, "--profile", "nginx_access", str(gz)],
                capture_output=True, text=True,
            )
            dt = time.perf_counter() - t0
            rss_after = _peak_rss_kib()
            tracemalloc.stop()
            self.assertEqual(r.returncode, 0, r.stderr)
            delta = rss_after - rss_before
            print(f"[stream] {STREAM_LINES:,} lines in {dt:.2f}s "
                  f"({_fmt_hz(STREAM_LINES, dt)}), ΔRSS {delta:,}KiB "
                  f"→ stdout {len(r.stdout):,}B, aggregated to {len(r.stdout.splitlines())} lines")
            self.assertLess(dt, MAX_STREAM_SEC,
                            f"stream perf regression: {dt:.2f}s > {MAX_STREAM_SEC}s")
            # Cube has fixed cardinality (status × method × path_root),
            # so memory should NOT scale with line count.
            self.assertLess(rss_after, MAX_RSS_KIB,
                            f"stream memory blow-up: {rss_after}KiB > {MAX_RSS_KIB}KiB")
        finally:
            shutil.rmtree(td, ignore_errors=True)


class ContentFilterPerfTests(unittest.TestCase):
    def test_content_filter_prescan(self):
        td = Path(tempfile.mkdtemp(prefix="dyn_bench_"))
        try:
            for i in range(2000):
                (td / f"f{i}.txt").write_text(
                    "TODO here\n" if i % 5 == 0 else "clean line\n"
                )
            t0 = time.perf_counter()
            r = subprocess.run(
                ["python3", DYN, "-p",
                 '{"dimensions":["name"],"extract":[{"type":"preset","preset":"paths"}],'
                 '"scan":{"content_match":["TODO"]},"output":{"format":"compact","max_lines":10}}',
                 str(td)],
                capture_output=True, text=True,
            )
            dt = time.perf_counter() - t0
            print(f"[content-filter] 2000 files, TODO in 20% → {dt:.2f}s")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertLess(dt, 5.0)
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    # Print environment header for reproducibility.
    print(f"cubest bench: HEAVY={int(HEAVY)}, "
          f"N_RECORDS={N_RECORDS:,}, N_FILES={N_FILES:,}, "
          f"STREAM_LINES={STREAM_LINES:,}, py={sys.version.split()[0]}")
    unittest.main(verbosity=2)
