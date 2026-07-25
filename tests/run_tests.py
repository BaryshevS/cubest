#!/usr/bin/env python3
"""Self-contained tests for cubest. Run with `python3 run_tests.py`."""

import gzip
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cubest  # noqa: E402
from cubest import (  # noqa: E402
    OlapCube, Extractor, should_scan, dir_pruned, passes_filters,
    _match_pattern, _hbytes,
)


DYN = str(ROOT / "cubest.py")


def _run(args, cwd=None):
    r = subprocess.run(["python3", DYN, *args], capture_output=True,
                       text=True, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


class MatchPatternTests(unittest.TestCase):
    def test_basename_glob(self):
        self.assertTrue(_match_pattern("a/b/foo.py", "foo.py", "*.py"))
        self.assertFalse(_match_pattern("a/b/foo.js", "foo.js", "*.py"))

    def test_dir_pattern(self):
        self.assertTrue(_match_pattern("node_modules/x/y.js", "y.js", "node_modules/"))
        self.assertFalse(_match_pattern("a/b/foo.py", "foo.py", "node_modules/"))
        # dir pattern must not match a plain file with the same name
        self.assertFalse(_match_pattern("node_modules", "node_modules", "node_modules/"))

    def test_anchored(self):
        self.assertTrue(_match_pattern("README.md", "README.md", "/README.md"))
        self.assertFalse(_match_pattern("src/README.md", "README.md", "/README.md"))

    def test_double_star(self):
        self.assertTrue(_match_pattern("docs/en/api/x.md", "x.md", "docs/**/*.md"))

    def test_substring_legacy(self):
        # bare "test" still matches paths containing test
        self.assertTrue(_match_pattern("a/tests/x.py", "x.py", "test"))


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        (Path(self.td) / "keep.py").write_text("x = 1")
        (Path(self.td) / "skip.log").write_text("log")
        os.makedirs(f"{self.td}/node_modules")
        (Path(self.td) / "node_modules" / "junk.js").write_text("")
        os.makedirs(f"{self.td}/keep_dir")
        (Path(self.td) / "keep_dir" / "a.py").write_text("y = 2")

    def tearDown(self):
        import shutil; shutil.rmtree(self.td, ignore_errors=True)

    def test_default_include_all(self):
        root = Path(self.td)
        p = root / "keep.py"
        self.assertTrue(should_scan(p, root, [], []))

    def test_exclude_glob(self):
        root = Path(self.td)
        p = root / "skip.log"
        self.assertFalse(should_scan(p, root, ["*"], ["*.log"]))

    def test_dir_exclude(self):
        root = Path(self.td)
        p = root / "node_modules" / "junk.js"
        self.assertFalse(should_scan(p, root, [], ["node_modules/"]))
        d = root / "node_modules"
        self.assertTrue(dir_pruned(d, root, ["node_modules/"]))

    def test_negation(self):
        # Include only *.py but NOT keep_dir/*
        root = Path(self.td)
        inc = ["*.py"]
        exc = ["keep_dir/"]
        self.assertTrue(should_scan(root / "keep.py", root, inc, exc))
        self.assertFalse(should_scan(root / "keep_dir" / "a.py", root, inc, exc))


class CubeTests(unittest.TestCase):
    def test_count_no_double(self):
        cube = OlapCube(["a", "b"], [{"name": "count", "type": "count"}])
        for _ in range(3):
            cube.add({"a": "x", "b": "y"})
        out = cube.format_flat()
        self.assertIn("x>y\t3\tcount=3", out)
        tree = cube.format_tree()
        # rollup should not double-count when measure is 'count'
        self.assertIn("x\t3\tcount=3", tree)
        self.assertIn("  y\t3\tcount=3", tree)

    def test_sum_and_avg(self):
        cube = OlapCube(["g"], [
            {"name": "s", "type": "sum", "field": "v"},
            {"name": "a", "type": "avg", "field": "v"},
        ])
        for v in (10, 20, 30):
            cube.add({"g": "one", "v": v})
        out = cube.format_flat()
        self.assertIn("s=60.0", out)
        self.assertIn("a=20.000", out)

    def test_percentile_p95(self):
        import random as _r
        _r.seed(0)
        cube = OlapCube(["g"], [
            {"name": "p50", "type": "p50", "field": "v"},
            {"name": "p95", "type": "p95", "field": "v"},
            {"name": "p99", "type": "p99", "field": "v"},
        ])
        # 0..999 uniform
        for v in range(1000):
            cube.add({"g": "one", "v": v})
        rolled = cube._rollup(cube.data["one"])
        # approx p50~500, p95~950, p99~990 with 128-sample reservoir → ±10%
        self.assertTrue(400 < rolled["p50"] < 600, rolled["p50"])
        self.assertTrue(850 < rolled["p95"] < 999, rolled["p95"])
        self.assertTrue(900 < rolled["p99"] < 999, rolled["p99"])

    def test_percentile_rollup_merge(self):
        import random as _r
        _r.seed(1)
        cube = OlapCube(["a", "b"], [
            {"name": "p90", "type": "p90", "field": "v", "sample_size": 256},
        ])
        for v in range(500):
            cube.add({"a": "x", "b": "y1", "v": v})
        for v in range(500, 1000):
            cube.add({"a": "x", "b": "y2", "v": v})
        rolled = cube._rollup(cube.data["x"])
        # combined 0..999, p90 ~ 900
        self.assertTrue(800 < rolled["p90"] < 990, rolled["p90"])

    def test_min_max(self):
        cube = OlapCube(["g"], [
            {"name": "mn", "type": "min", "field": "v"},
            {"name": "mx", "type": "max", "field": "v"},
        ])
        for v in (10, 3, 42, 7):
            cube.add({"g": "one", "v": v})
        rolled = cube._rollup(cube.data["one"])
        self.assertEqual(rolled["mn"], 3)
        self.assertEqual(rolled["mx"], 42)

    def test_csv_format(self):
        cube = OlapCube(["a"], [{"name": "n", "type": "count"}])
        cube.add({"a": "x"}); cube.add({"a": "x"}); cube.add({"a": "y"})
        out = cube.format_csv()
        self.assertEqual(out.splitlines()[0], "a,count,n")
        self.assertIn("x,2,2", out)
        self.assertIn("y,1,1", out)

    def test_max_lines_truncation(self):
        cube = OlapCube(["a"], [{"name": "n", "type": "count"}])
        for i in range(20):
            cube.add({"a": f"k{i}"})
        out = cube.format_flat(max_lines=5)
        self.assertEqual(len(out.splitlines()), 6)  # 5 + "…"
        self.assertIn("more", out.splitlines()[-1])


class ExtractorTests(unittest.TestCase):
    def test_regex_named_groups_and_coerce(self):
        ext = Extractor([{"type": "regex", "pattern": r"(?P<code>\d+)\s+(?P<t>[0-9.]+)"}])
        recs = ext.extract("200 0.123\n404 1.5\n", "f")
        self.assertEqual(recs[0]["code"], 200)
        self.assertEqual(recs[0]["t"], 0.123)
        self.assertEqual(recs[1]["code"], 404)

    def test_preset_paths(self):
        ext = Extractor([{"type": "preset", "preset": "paths"}])
        recs = ext.extract_line("", "docs/api/README.md", 0)
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["ext"], "md")
        self.assertEqual(r["basename"], "README")
        self.assertEqual(r["top"], "docs")
        self.assertEqual(r["depth"], 2)

    def test_preset_funcs(self):
        code = "def foo():\n    pass\nclass Bar:\n    pass\n"
        ext = Extractor([{"type": "preset", "preset": "funcs"}])
        recs = ext.extract(code, "x.py")
        self.assertEqual(sorted(r["name"] for r in recs), ["Bar", "foo"])
        self.assertTrue(all(r["lang"] == "py" for r in recs))

    def test_preset_funcs_python_nesting(self):
        code = (
            "class Outer:\n"
            "    def method_a(self):\n"
            "        def nested():\n"
            "            pass\n"
            "    def method_b(self):\n"
            "        pass\n"
        )
        ext = Extractor([{"type": "preset", "preset": "funcs"}])
        recs = {r["name"]: r for r in ext.extract(code, "x.py")}
        self.assertEqual(recs["Outer"]["parent"], "")
        self.assertEqual(recs["method_a"]["parent"], "Outer")
        self.assertEqual(recs["nested"]["parent"], "method_a")
        self.assertEqual(recs["nested"]["depth"], 2)
        self.assertEqual(recs["method_b"]["parent"], "Outer")

    def test_preset_funcs_multilang(self):
        ext = Extractor([{"type": "preset", "preset": "funcs"}])
        js = "export function handler(req) {}\nclass Foo {}\n"
        recs = ext.extract(js, "app.js")
        names = {r["name"] for r in recs}
        self.assertEqual(names, {"handler", "Foo"})
        self.assertTrue(all(r["lang"] == "js" for r in recs))
        go = "func DoStuff(x int) int { return x }\n"
        recs = ext.extract(go, "main.go")
        self.assertEqual(recs[0]["name"], "DoStuff")
        self.assertEqual(recs[0]["lang"], "go")

    def test_line_by_line_stream_regex(self):
        ext = Extractor([{"type": "regex", "multiline": False,
                          "pattern": r"(?P<lvl>ERROR|WARN)"}])
        recs = ext.extract_line("2026 ERROR boom", "app.log", 42)
        self.assertEqual(recs[0]["lvl"], "ERROR")
        self.assertEqual(recs[0]["_line"], 42)


class FilterTests(unittest.TestCase):
    def test_expr_with_builtins(self):
        self.assertTrue(passes_filters({"x": 5}, ["x > 3", "len(str(x)) == 1"]))
        self.assertFalse(passes_filters({"x": 5}, ["x < 3"]))

    def test_string_ops(self):
        self.assertTrue(passes_filters({"path": "src/app.py"},
                                       ["'src' in path", "path.endswith('.py')"]))

    def test_no_builtins_leak(self):
        # __import__ must not be available
        self.assertFalse(passes_filters({"x": 1}, ["__import__('os')"]))


class CsvPresetTests(unittest.TestCase):
    def test_csv_header_and_coerce(self):
        c = "Campaign,Device,Impressions,Cost\nBrand,mobile,120000,240.5\nBrand,desktop,85000,170.2\n"
        ext = Extractor([{"type": "preset", "preset": "csv"}])
        recs = ext.extract(c, "ads.csv")
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["campaign"], "Brand")  # slugged header
        self.assertEqual(recs[0]["device"], "mobile")
        self.assertEqual(recs[0]["impressions"], 120000)  # int coerced
        self.assertAlmostEqual(recs[0]["cost"], 240.5)   # float coerced

    def test_tsv_preset(self):
        c = "a\tb\tn\nx\ty\t5\n"
        ext = Extractor([{"type": "preset", "preset": "tsv"}])
        recs = ext.extract(c, "x.tsv")
        self.assertEqual(recs[0]["a"], "x")
        self.assertEqual(recs[0]["n"], 5)

    def test_csv_no_header(self):
        c = "brand,mobile,120\nbrand,desktop,85\n"
        ext = Extractor([{"type": "preset", "preset": "csv", "header": False}])
        recs = ext.extract(c, "x.csv")
        self.assertEqual(recs[0]["col_0"], "brand")
        self.assertEqual(recs[0]["col_2"], 120)
        self.assertEqual(len(recs), 2)

    def test_csv_explicit_headers(self):
        c = "brand,mobile,120\nbrand,desktop,85\n"
        ext = Extractor([{"type": "preset", "preset": "csv",
                          "header": ["campaign", "device", "clicks"]}])
        recs = ext.extract(c, "x.csv")
        self.assertEqual(recs[0]["campaign"], "brand")
        self.assertEqual(recs[0]["clicks"], 120)

    def test_csv_with_semicolon_sep(self):
        c = "a;b\nx;5\n"
        ext = Extractor([{"type": "preset", "preset": "csv", "sep": ";"}])
        recs = ext.extract(c, "x.csv")
        self.assertEqual(recs[0]["b"], 5)


class SeoPresetsTests(unittest.TestCase):
    HTML = """<!DOCTYPE html><html lang="en">
<head>
<title>Buy coffee — London</title>
<meta name="description" content="Fresh roast, next-day delivery in London">
<meta name="keywords" content="coffee, london, delivery">
<link rel="canonical" href="https://ex.com/coffee">
<meta property="og:title" content="Coffee">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">{}</script>
</head><body>
<h1>Coffee catalog</h1>
<h2>Arabica</h2><h2>Robusta</h2>
<h3>Ethiopia</h3><h3>Colombia</h3>
</body></html>"""

    def test_html_meta_extraction(self):
        ext = Extractor([{"type": "preset", "preset": "html_meta"}])
        recs = ext.extract(self.HTML, "coffee.html")
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["title"], "Buy coffee — London")
        self.assertIn("Fresh", r["description"])
        self.assertEqual(r["lang"], "en")
        self.assertEqual(r["canonical"], "https://ex.com/coffee")
        self.assertEqual(r["h1_count"], 1)
        self.assertEqual(r["h1_first"], "Coffee catalog")
        self.assertEqual(r["h2_count"], 2)
        self.assertEqual(r["h3_count"], 2)
        self.assertEqual(r["has_schema"], 1)
        self.assertEqual(r["twitter_card"], "summary")

    def test_html_headings_tree(self):
        ext = Extractor([{"type": "preset", "preset": "html_headings"}])
        recs = ext.extract(self.HTML, "coffee.html")
        levels = [r["level"] for r in recs]
        self.assertEqual(sorted(levels), [1, 2, 2, 3, 3])
        h1 = [r for r in recs if r["level"] == 1][0]
        self.assertEqual(h1["title"], "Coffee catalog")

    def test_sitemap_extraction(self):
        xml = """<?xml version="1.0"?>
<urlset><url>
<loc>https://ex.com/blog/coffee/arabica</loc>
<priority>0.8</priority>
<lastmod>2026-01-15</lastmod>
</url><url>
<loc>https://ex.com/blog/tea</loc>
<priority>0.6</priority>
</url></urlset>"""
        ext = Extractor([{"type": "preset", "preset": "sitemap"}])
        recs = ext.extract(xml, "sitemap.xml")
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["host"], "ex.com")
        self.assertEqual(recs[0]["section_1"], "blog")
        self.assertEqual(recs[0]["section_2"], "coffee")
        self.assertEqual(recs[0]["depth"], 3)
        self.assertAlmostEqual(recs[0]["priority"], 0.8)


class SddPresetsTests(unittest.TestCase):
    def test_md_frontmatter_batch(self):
        content = "---\ntype: spec\nstatus: draft\nowner: alice\n---\n# body\n"
        ext = Extractor([{"type": "preset", "preset": "md_frontmatter"}])
        recs = ext.extract(content, "specs/a.md")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["type"], "spec")
        self.assertEqual(recs[0]["status"], "draft")
        self.assertEqual(recs[0]["owner"], "alice")

    def test_md_frontmatter_missing(self):
        ext = Extractor([{"type": "preset", "preset": "md_frontmatter"}])
        recs = ext.extract("# no frontmatter\n", "x.md")
        self.assertEqual(recs, [])

    def test_md_checklist_batch(self):
        c = "- [x] done one\n- [ ] todo one\n- [X] done two\n- normal item\n"
        ext = Extractor([{"type": "preset", "preset": "md_checklist"}])
        recs = ext.extract(c, "todo.md")
        states = [r["state"] for r in recs]
        self.assertEqual(states.count("done"), 2)
        self.assertEqual(states.count("todo"), 1)

    def test_md_checklist_streaming(self):
        ext = Extractor([{"type": "preset", "preset": "md_checklist"}])
        recs = ext.extract_line("- [x] shipped", "log.md", 7)
        self.assertEqual(recs[0]["state"], "done")
        self.assertEqual(recs[0]["_line"], 7)


class OutputFormatsTests(unittest.TestCase):
    def _cube(self):
        cube = OlapCube(["kind"], [{"name": "n", "type": "count"}])
        cube.add({"kind": "a"}); cube.add({"kind": "a"}); cube.add({"kind": "b"})
        return cube

    def test_yaml_output(self):
        out = self._cube().format_yaml()
        self.assertIn("a:", out)
        self.assertIn("n: 2", out)

    def test_md_table_output(self):
        out = self._cube().format_md_table()
        self.assertIn("| kind | count | n |", out)
        self.assertIn("| a | 2 | 2 |", out)

    def test_json_output(self):
        out = self._cube().format_json()
        parsed = __import__("json").loads(out)
        self.assertEqual(parsed["a"]["n"], 2)

    def _edge_cube(self):
        cube = OlapCube(["src", "dst"], [{"name": "n", "type": "count"}])
        for _ in range(3):
            cube.add({"src": "A", "dst": "B"})
        cube.add({"src": "A", "dst": "C"})
        return cube

    def test_dot_output(self):
        out = self._edge_cube().format_dot()
        self.assertIn("digraph", out)
        self.assertIn('"A" -> "B"', out)
        self.assertIn('label="3"', out)

    def test_mermaid_output(self):
        out = self._edge_cube().format_mermaid()
        self.assertTrue(out.startswith("flowchart LR"))
        self.assertIn("-->|3|", out)

    def test_plantuml_output(self):
        out = self._edge_cube().format_plantuml()
        self.assertIn("@startuml", out)
        self.assertIn("@enduml", out)
        self.assertIn(" : 3", out)

    def test_drawio_output(self):
        out = self._edge_cube().format_drawio()
        self.assertIn("<mxfile", out)
        self.assertIn('value="A"', out)
        self.assertIn('source="', out)

    def test_xml_output(self):
        out = self._edge_cube().format_xml()
        self.assertIn("<?xml", out)
        self.assertIn('key="A"', out)
        self.assertIn('count="', out)

    def test_echarts_html(self):
        out = self._edge_cube().format_echarts(chart_type="sankey", title="t")
        self.assertIn("<!DOCTYPE html", out)
        self.assertIn("echarts.min.js", out)
        self.assertIn('"source": "A"', out)
        self.assertIn('"chart_type": "sankey"', out)
        # tree + graph views must be present in AVAIL and VIEWS
        self.assertIn("tree:", out)
        self.assertIn("graph:", out)
        self.assertIn("optTree", out)
        self.assertIn("optGraph", out)

    def test_echarts_auto_hierarchical(self):
        cube = OlapCube(["kind", "file"], [{"name": "n", "type": "count"}])
        cube.add({"kind": "def", "file": "a.py"})
        cube.add({"kind": "class", "file": "a.py"})
        out = cube.format_echarts(chart_type="auto")
        # 2 dims with 2 top keys → treemap
        self.assertIn('"chart_type": "treemap"', out)


class HbytesTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(_hbytes(0), "0B")
        self.assertEqual(_hbytes(1023), "1023B")
        self.assertEqual(_hbytes(1024), "1.0KiB")
        self.assertEqual(_hbytes(1024 * 1024 * 1.5), "1.5MiB")


class PathPrefixTests(unittest.TestCase):
    def test_path_1_to_5(self):
        ext = Extractor([{"type": "preset", "preset": "paths"}])
        recs = ext.extract_line("", "a/b/c/d/file.py", 0)
        r = recs[0]
        self.assertEqual(r["path_1"], "a")
        self.assertEqual(r["path_2"], "a/b")
        self.assertEqual(r["path_3"], "a/b/c")
        self.assertEqual(r["path_4"], "a/b/c/d")
        self.assertEqual(r["path_5"], "")  # only 4 dir parts

    def test_root_file(self):
        ext = Extractor([{"type": "preset", "preset": "paths"}])
        recs = ext.extract_line("", "file.py", 0)
        r = recs[0]
        self.assertEqual(r["path_1"], "")
        self.assertEqual(r["depth"], 0)


class ContentFilterTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        (Path(self.td) / "a.py").write_text("# TODO: fix this\nimport os\n")
        (Path(self.td) / "b.py").write_text("# clean file\n")
        (Path(self.td) / "c.py").write_text("# TODO plus @deprecated marker\n")

    def tearDown(self):
        import shutil; shutil.rmtree(self.td, ignore_errors=True)

    def test_must_have(self):
        code, out, err = _run([
            "-p",
            '{"dimensions":["name"],"measures":[{"name":"n","type":"count"}],'
            '"extract":[{"type":"preset","preset":"paths"}],'
            '"scan":{"content_match":["TODO"]},'
            '"output":{"format":"compact"}}',
            self.td,
        ])
        self.assertEqual(code, 0, err)
        self.assertIn("a.py: 1", out)
        self.assertIn("c.py: 1", out)
        self.assertNotIn("b.py: 1", out)

    def test_must_not(self):
        code, out, err = _run([
            "-p",
            '{"dimensions":["name"],"measures":[{"name":"n","type":"count"}],'
            '"extract":[{"type":"preset","preset":"paths"}],'
            '"scan":{"content_match":["TODO"],"content_not":["@deprecated"]},'
            '"output":{"format":"compact"}}',
            self.td,
        ])
        self.assertEqual(code, 0, err)
        self.assertIn("a.py: 1", out)
        self.assertNotIn("c.py: 1", out)


class CliIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        p = Path(self.td)
        (p / "hello.py").write_text("def a():\n    pass\nclass B:\n    pass\n")
        (p / "world.py").write_text("def c():\n    pass\n")
        (p / "README.md").write_text("# t\n## s\n")
        os.makedirs(p / "node_modules")
        (p / "node_modules" / "junk.js").write_text("function x(){}")

    def tearDown(self):
        import shutil; shutil.rmtree(self.td, ignore_errors=True)

    def test_file_tree_prunes_node_modules(self):
        code, out, err = _run(["--profile", "file_tree", self.td])
        self.assertEqual(code, 0, err)
        self.assertNotIn("node_modules", out)
        self.assertIn("py", out)

    def test_code_stats(self):
        code, out, err = _run(["--profile", "code_stats", self.td])
        self.assertEqual(code, 0, err)
        self.assertIn("def", out)
        self.assertIn("class", out)

    def test_doc_structure(self):
        code, out, err = _run(["--profile", "doc_structure", self.td])
        self.assertEqual(code, 0, err)
        self.assertIn("README.md", out)

    def test_inline_json_profile(self):
        prof = '{"dimensions":["ext"],"measures":[{"name":"count","type":"count"}],' \
               '"extract":[{"type":"preset","preset":"paths"}],' \
               '"scan":{"exclude":["node_modules/"]},' \
               '"output":{"format":"csv"}}'
        code, out, err = _run(["--profile", prof, self.td])
        self.assertEqual(code, 0, err)
        self.assertIn("ext,count", out)
        self.assertIn("py,2", out)

    def test_gzip_streaming(self):
        # Fake nginx-like log, gzipped
        line = (
            '10.0.0.1 - - [10/Jul/2026:00:00:00 +0000] '
            '"GET /api/v1/users HTTP/1.1" 200 512 "-" "curl/8" 0.045\n'
        )
        gz = Path(self.td) / "access.log.gz"
        with gzip.open(gz, "wt") as fh:
            for _ in range(50):
                fh.write(line)
        code, out, err = _run(["--profile", "nginx_access", str(gz)])
        self.assertEqual(code, 0, err)
        self.assertIn("api", out)  # path_root
        self.assertIn("hits=", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
