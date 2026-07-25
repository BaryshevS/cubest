#!/usr/bin/env python3
"""
cubest.py — Single-pass OLAP indexer for Claude Code skill.

Scans files (plain or .gz, streaming or batch), extracts records via regex or
presets, aggregates them into an in-memory hierarchical cube, and prints a
compact tree / breadcrumb list / CSV / JSON. Designed to replace long chains
of `grep`+`cat` and to keep large-scan output token-cheap.

Usage:
    python cubest.py --profile file_tree .
    python cubest.py --profile api_routes ./src
    python cubest.py --profile nginx_access /var/log/nginx/access.log.gz
    python cubest.py --profile - < profile.yaml ./src
    python cubest.py --profile '{"dimensions":["kind"],...}' ./src
"""

import os
import re
import io
import csv as _csv_lib
import sys
import gzip
import json
import random
import argparse
from pathlib import Path
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional, Iterable

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Optional exact-percentile backend. When installed (`pip install tdigest`)
# it replaces reservoir sampling for p50/p90/p95/p99 measures — a lot more
# accurate on long-tailed distributions at the cost of an extra dependency.
try:
    from tdigest import TDigest as _TDigest
    HAS_TDIGEST = True
except ImportError:
    HAS_TDIGEST = False


# ---------------------------------------------------------------------------
# OLAP cube
# ---------------------------------------------------------------------------

_MEASURE_TYPE_Q = {"p50": 0.5, "p90": 0.9, "p95": 0.95, "p99": 0.99}


class _Reservoir:
    """Fixed-size reservoir sampling (Vitter's algorithm R) → memory O(k).

    Approximate quantiles via sort of the buffer. Rollup: proportional
    resample of the two parent buffers so total size stays bounded.
    """
    __slots__ = ("k", "n", "buf")

    def __init__(self, k: int = 128, buf=None, n: int = 0):
        self.k = k
        self.n = n
        self.buf = buf if buf is not None else []

    def add(self, v):
        self.n += 1
        if len(self.buf) < self.k:
            self.buf.append(v)
        else:
            i = random.randint(0, self.n - 1)
            if i < self.k:
                self.buf[i] = v

    def quantile(self, q: float) -> float:
        if not self.buf:
            return 0.0
        s = sorted(self.buf)
        if len(s) == 1:
            return s[0]
        pos = q * (len(s) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(s) - 1)
        frac = pos - lo
        return s[lo] * (1 - frac) + s[hi] * frac

    @classmethod
    def merge(cls, a, b, k: int):
        """Weighted-proportional merge — approximate but bounded."""
        if a is None:
            return b
        if b is None:
            return a
        total = a.n + b.n
        if total == 0:
            return cls(k)
        if len(a.buf) + len(b.buf) <= k:
            return cls(k, list(a.buf) + list(b.buf), total)
        from_a = min(len(a.buf), max(1, int(round(k * a.n / total))))
        from_b = min(len(b.buf), k - from_a)
        buf = random.sample(a.buf, from_a) + random.sample(b.buf, from_b)
        return cls(k, buf, total)


class OlapCube:
    """In-memory OLAP cube with hierarchical dimensions."""

    def __init__(self, dimensions: List[str], measures: List[Dict]):
        self.dimensions = dimensions
        self.measures = measures
        self.data: Dict = {}

    def add(self, record: Dict):
        node = self.data
        rget = record.get
        for dim in self.dimensions:
            val = rget(dim)
            if val is None and not dim.startswith("_"):
                val = rget("_" + dim)
            if val is None or val == "":
                val = "---"
            child = node.get(val)
            if child is None:
                child = {"_meta": {"count": 0}}
                node[val] = child
                meta = child["_meta"]
            else:
                meta = child.setdefault("_meta", {"count": 0})
            meta["count"] += 1
            node = child

        for m in self.measures:
            mtype = m.get("type", "count")
            mname = m["name"]
            if mtype == "count":
                node[mname] = node.get(mname, 0) + 1
            elif mtype == "sum":
                field = m.get("field", mname)
                node[mname] = node.get(mname, 0) + _num(rget(field, 0))
            elif mtype == "avg":
                field = m.get("field", mname)
                meta_avg = node.setdefault("_meta_avg", {})
                sum_key = mname + "_sum"
                new_sum = meta_avg.get(sum_key, 0) + _num(rget(field, 0))
                meta_avg[sum_key] = new_sum
                node[mname] = new_sum / node["_meta"]["count"]
            elif mtype in ("min", "max"):
                field = m.get("field", mname)
                v = _num(rget(field, 0))
                cur = node.get(mname)
                if cur is None:
                    node[mname] = v
                else:
                    node[mname] = v if (mtype == "min") == (v < cur) else cur
            elif mtype in ("p50", "p90", "p95", "p99", "percentile"):
                field = m.get("field", mname)
                v = _num(rget(field, 0))
                k = m.get("sample_size", 128)
                res_key = "_res_" + mname
                res = node.get(res_key)
                if res is None:
                    res = _Reservoir(k)
                    node[res_key] = res
                res.add(v)
                q = m.get("q") or _MEASURE_TYPE_Q.get(mtype, 0.5)
                node[mname] = res.quantile(q)

    def _rollup(self, node: Dict) -> Dict:
        result = {"_total": node.get("_meta", {}).get("count", 0)}
        is_leaf = not any(
            isinstance(v, dict) and k not in ("_meta", "_meta_avg")
            for k, v in node.items()
        )

        if is_leaf:
            for m in self.measures:
                mname = m["name"]
                if mname in node:
                    result[mname] = node[mname]
                    if m.get("type") == "avg":
                        sum_key = f"{mname}_sum"
                        result[f"_{mname}_sum"] = node.get("_meta_avg", {}).get(sum_key, 0)
                    if m.get("type") in ("p50", "p90", "p95", "p99", "percentile"):
                        res = node.get("_res_" + mname)
                        if res is not None:
                            result["_res_" + mname] = res
        else:
            for key, child in node.items():
                if not isinstance(child, dict) or key in ("_meta", "_meta_avg"):
                    continue
                child_res = self._rollup(child)
                for m in self.measures:
                    mname = m["name"]
                    mtype = m.get("type", "count")
                    if mname not in child_res:
                        continue
                    if mtype in ("count", "sum"):
                        result[mname] = result.get(mname, 0) + child_res[mname]
                    elif mtype == "avg":
                        c_sum = child_res.get(f"_{mname}_sum", 0)
                        p_sum = result.get(f"_{mname}_sum", 0)
                        result[f"_{mname}_sum"] = p_sum + c_sum
                    elif mtype == "min":
                        result[mname] = child_res[mname] if mname not in result \
                            else min(result[mname], child_res[mname])
                    elif mtype == "max":
                        result[mname] = child_res[mname] if mname not in result \
                            else max(result[mname], child_res[mname])
                    elif mtype in ("p50", "p90", "p95", "p99", "percentile"):
                        k = m.get("sample_size", 128)
                        res_key = "_res_" + mname
                        child_res_obj = child_res.get(res_key)
                        merged = _Reservoir.merge(
                            result.get(res_key), child_res_obj, k)
                        if merged is not None:
                            result[res_key] = merged
                            q = m.get("q") or _MEASURE_TYPE_Q.get(mtype, 0.5)
                            result[mname] = merged.quantile(q)

        total = result["_total"]
        for m in self.measures:
            if m.get("type") == "avg":
                sum_key = f"_{m['name']}_sum"
                if sum_key in result and total > 0:
                    result[m["name"]] = result[sum_key] / total
        return result

    # ---- formatters ------------------------------------------------------

    def _fmt_measures(self, values: Dict, human_bytes: bool) -> List[str]:
        out = []
        for m in self.measures:
            mname = m["name"]
            if mname not in values:
                continue
            val = values[mname]
            mtype = m.get("type", "count")
            field = m.get("field", mname)
            if human_bytes and (field == "size" or "byte" in mname.lower()):
                out.append(f"{mname}={_hbytes(val)}")
            elif mtype == "avg" or mtype in ("p50", "p90", "p95", "p99", "percentile"):
                out.append(f"{mname}={val:.3f}")
            elif mtype == "sum":
                out.append(f"{mname}={val:.1f}")
            else:
                out.append(f"{mname}={int(val)}" if not isinstance(val, float)
                           else f"{mname}={val:g}")
        return out

    def _format_tree(self, node: Dict, depth: int, top_n: Optional[int],
                     min_count: Optional[int], human_bytes: bool,
                     max_depth: Optional[int], lines: List[str]):
        if max_depth is not None and depth >= max_depth:
            return
        children = []
        for k, v in node.items():
            if k in ("_meta", "_meta_avg") or not isinstance(v, dict):
                continue
            cnt = v.get("_meta", {}).get("count", 0)
            if min_count is not None and cnt < min_count:
                continue
            children.append((k, v, cnt))
        children.sort(key=lambda x: -x[2])
        if top_n is not None:
            children = children[:top_n]

        indent = "  " * depth
        for key, child, count in children:
            rolled = self._rollup(child)
            m_strs = self._fmt_measures(rolled, human_bytes)
            if m_strs:
                lines.append(f"{indent}{key}\t{count}\t{', '.join(m_strs)}")
            else:
                lines.append(f"{indent}{key}\t{count}")
            self._format_tree(child, depth + 1, top_n, min_count, human_bytes,
                              max_depth, lines)

    def format_tree(self, top_n=None, min_count=None, human_bytes=False,
                    max_depth=None, max_lines=None) -> str:
        lines: List[str] = []
        self._format_tree(self.data, 0, top_n, min_count, human_bytes,
                          max_depth, lines)
        return _clip(lines, max_lines)

    def format_flat(self, top_n=None, min_count=None, human_bytes=False,
                    max_lines=None, sep=">") -> str:
        """Breadcrumb rows: dim1>dim2>...>dimN <TAB> count <TAB> measures."""
        rows: List[tuple] = []

        def walk(node: Dict, path: List[str]):
            children = [(k, v) for k, v in node.items()
                        if isinstance(v, dict) and k not in ("_meta", "_meta_avg")]
            if not children:
                cnt = node.get("_meta", {}).get("count", 0)
                if min_count is not None and cnt < min_count:
                    return
                m_strs = self._fmt_measures(self._rollup(node), human_bytes)
                rows.append((path, cnt, m_strs))
                return
            children.sort(key=lambda x: -x[1].get("_meta", {}).get("count", 0))
            if top_n is not None:
                children = children[:top_n]
            for k, v in children:
                walk(v, path + [str(k)])

        walk(self.data, [])
        rows.sort(key=lambda r: -r[1])
        lines = []
        for path, cnt, m_strs in rows:
            key = sep.join(path) if path else "(root)"
            suffix = "\t" + ", ".join(m_strs) if m_strs else ""
            lines.append(f"{key}\t{cnt}{suffix}")
        return _clip(lines, max_lines)

    def format_compact(self, max_lines=None) -> str:
        def count_items(node):
            if "_meta" in node:
                return node["_meta"]["count"]
            return sum(count_items(v) for v in node.values() if isinstance(v, dict))
        items = []
        for k, v in self.data.items():
            if not isinstance(v, dict) or k in ("_meta", "_meta_avg"):
                continue
            items.append((k, count_items(v)))
        items.sort(key=lambda x: x[1], reverse=True)
        lines = [f"{k}: {v}" for k, v in items]
        return _clip(lines, max_lines)

    def format_csv(self, human_bytes=False, max_lines=None) -> str:
        headers = list(self.dimensions) + ["count"] + [m["name"] for m in self.measures]
        rows = [",".join(headers)]

        def walk(node, path):
            children = [(k, v) for k, v in node.items()
                        if isinstance(v, dict) and k not in ("_meta", "_meta_avg")]
            if not children:
                cnt = node.get("_meta", {}).get("count", 0)
                rolled = self._rollup(node)
                cells = list(path) + [str(cnt)]
                for m in self.measures:
                    v = rolled.get(m["name"], "")
                    if isinstance(v, float):
                        v = f"{v:.4f}"
                    cells.append(str(v))
                rows.append(",".join(_csv(c) for c in cells))
                return
            for k, v in children:
                walk(v, path + [str(k)])

        walk(self.data, [])
        if max_lines is not None and len(rows) - 1 > max_lines:
            truncated = len(rows) - 1 - max_lines
            rows = rows[:1 + max_lines] + [f"# (+{truncated} more)"]
        return "\n".join(rows)

    def format_json(self) -> str:
        return json.dumps(self.data, indent=2, ensure_ascii=False, default=str)

    def _iter_edges(self, min_count=None):
        """Yield ((src, dst), weight) pairs for the first two dimensions.

        Every leaf whose path is >= 2 becomes an edge; deeper dimensions are
        collapsed into the count."""
        edges: Dict[tuple, int] = {}

        def walk(node, path):
            children = [(k, v) for k, v in node.items()
                        if isinstance(v, dict) and k not in ("_meta", "_meta_avg")]
            if not children:
                if len(path) >= 2:
                    cnt = node.get("_meta", {}).get("count", 0)
                    if min_count is None or cnt >= min_count:
                        edges[(str(path[0]), str(path[1]))] = \
                            edges.get((str(path[0]), str(path[1])), 0) + cnt
                return
            for k, v in children:
                walk(v, path + [k])

        walk(self.data, [])
        return edges

    def format_mermaid(self, top_n=None, min_count=None, direction="LR") -> str:
        """Mermaid flowchart syntax. Works with 2 dimensions treated as edges."""
        if len(self.dimensions) < 2:
            return "%% mermaid output requires at least 2 dimensions"
        edges = self._iter_edges(min_count=min_count)
        ranked = sorted(edges.items(), key=lambda kv: -kv[1])
        if top_n is not None:
            ranked = ranked[:top_n]
        lines = [f"flowchart {direction}"]
        # mermaid identifiers must be safe; encode via node_N mapping
        node_id: Dict[str, str] = {}

        def nid(name: str) -> str:
            if name not in node_id:
                node_id[name] = f"n{len(node_id)}"
            return node_id[name]

        for (s, d), w in ranked:
            si, di = nid(s), nid(d)
            sl = s.replace('"', '\\"'); dl = d.replace('"', '\\"')
            lines.append(f'  {si}["{sl}"] -->|{w}| {di}["{dl}"]')
        return "\n".join(lines)

    def format_plantuml(self, top_n=None, min_count=None) -> str:
        """PlantUML component-style diagram from the first two dimensions."""
        if len(self.dimensions) < 2:
            return "' plantuml output requires at least 2 dimensions"
        edges = self._iter_edges(min_count=min_count)
        ranked = sorted(edges.items(), key=lambda kv: -kv[1])
        if top_n is not None:
            ranked = ranked[:top_n]
        nodes = set()
        for (s, d) in [kv[0] for kv in ranked]:
            nodes.add(s); nodes.add(d)
        node_id: Dict[str, str] = {}
        for n in sorted(nodes):
            node_id[n] = f"N{len(node_id)}"
        lines = ["@startuml", "skinparam componentStyle rectangle", ""]
        for n in sorted(nodes):
            safe = n.replace('"', '\\"')
            lines.append(f'component "{safe}" as {node_id[n]}')
        lines.append("")
        for (s, d), w in ranked:
            lines.append(f'{node_id[s]} --> {node_id[d]} : {w}')
        lines.append("@enduml")
        return "\n".join(lines)

    def format_drawio(self, top_n=None, min_count=None) -> str:
        """Minimal draw.io / diagrams.net XML — importable via File → Import.

        Layout is naive (grid), positions can be re-flowed in-app with Ctrl-L.
        """
        if len(self.dimensions) < 2:
            return "<!-- drawio output requires at least 2 dimensions -->"
        edges = self._iter_edges(min_count=min_count)
        ranked = sorted(edges.items(), key=lambda kv: -kv[1])
        if top_n is not None:
            ranked = ranked[:top_n]
        nodes = set()
        for (s, d) in [kv[0] for kv in ranked]:
            nodes.add(s); nodes.add(d)
        nodes_sorted = sorted(nodes)
        node_id = {n: f"n{i+2}" for i, n in enumerate(nodes_sorted)}

        def esc(s: str) -> str:
            return (s.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))

        cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
        cols = max(1, int(len(nodes_sorted) ** 0.5))
        for i, n in enumerate(nodes_sorted):
            x = (i % cols) * 180
            y = (i // cols) * 100
            cells.append(
                f'<mxCell id="{node_id[n]}" value="{esc(n)}" style="rounded=1;whiteSpace=wrap;" '
                f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="140" height="40" as="geometry"/></mxCell>'
            )
        for j, ((s, d), w) in enumerate(ranked):
            eid = f"e{j+1}"
            cells.append(
                f'<mxCell id="{eid}" style="endArrow=block;html=1;" edge="1" parent="1" '
                f'source="{node_id[s]}" target="{node_id[d]}" value="{w}">'
                f'<mxGeometry relative="1" as="geometry"/></mxCell>'
            )
        body = "\n    ".join(cells)
        return (
            '<mxfile host="app.diagrams.net">\n'
            '  <diagram name="cubest" id="dyn">\n'
            '    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" arrows="1" '
            'fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100">\n'
            '      <root>\n'
            f'        {body}\n'
            '      </root>\n'
            '    </mxGraphModel>\n'
            '  </diagram>\n'
            '</mxfile>'
        )

    # ---- echarts (HTML with CDN) ----------------------------------------

    def _to_hierarchy(self, min_count=None, max_children=None) -> List[Dict]:
        """Convert cube to ECharts nested `{name, value, children}` array."""
        def build(node, name):
            children = []
            for k, v in node.items():
                if not isinstance(v, dict) or k in ("_meta", "_meta_avg"):
                    continue
                child = build(v, str(k))
                if min_count is not None and child["value"] < min_count:
                    continue
                children.append(child)
            children.sort(key=lambda c: -c["value"])
            if max_children is not None:
                children = children[:max_children]
            value = (node.get("_meta", {}).get("count", 0)
                     if not children else sum(c["value"] for c in children))
            out = {"name": name, "value": value}
            if children:
                out["children"] = children
            return out

        roots = []
        for k, v in self.data.items():
            if not isinstance(v, dict) or k in ("_meta", "_meta_avg"):
                continue
            roots.append(build(v, str(k)))
        roots.sort(key=lambda c: -c["value"])
        if max_children is not None:
            roots = roots[:max_children]
        return roots

    def _to_edges_nodes(self, top_n=None, min_count=None):
        """For 2-dim cubes: return (nodes[], links[]) suitable for sankey/graph."""
        edges = self._iter_edges(min_count=min_count)
        ranked = sorted(edges.items(), key=lambda kv: -kv[1])
        if top_n is not None:
            ranked = ranked[:top_n]
        nodes_set = set()
        for (s, d), _ in ranked:
            nodes_set.add(s); nodes_set.add(d)
        # Sankey chokes on cycles — break by suffixing dst when equal to src
        cleaned = []
        for (s, d), w in ranked:
            if s == d:
                d = d + " "
                nodes_set.add(d)
            cleaned.append((s, d, w))
        return (
            [{"name": n} for n in sorted(nodes_set)],
            [{"source": s, "target": d, "value": w} for (s, d, w) in cleaned],
        )

    def _to_bar(self, top_n=None):
        """Flat one-level breakdown for a bar chart."""
        items = []
        for k, v in self.data.items():
            if not isinstance(v, dict) or k in ("_meta", "_meta_avg"):
                continue
            items.append((str(k), v.get("_meta", {}).get("count", 0)))
        items.sort(key=lambda x: -x[1])
        if top_n is not None:
            items = items[:top_n]
        return [x[0] for x in items], [x[1] for x in items]

    def _auto_chart_type(self) -> str:
        """Pick a sensible default chart type based on cube shape."""
        n_dims = len(self.dimensions)
        n_top_keys = sum(1 for k, v in self.data.items()
                         if isinstance(v, dict) and k not in ("_meta", "_meta_avg"))
        if n_dims == 1:
            return "bar"
        if n_dims == 2:
            # Many-to-many edges → sankey; balanced hierarchy → treemap
            return "sankey" if n_top_keys > 5 else "treemap"
        # ≥3 dims: sunburst for compactness, tree for deep hierarchies
        return "sunburst" if n_dims <= 4 else "tree"

    def format_echarts(self, chart_type: str = "auto", title: str = "cubest",
                       top_n=None, min_count=None) -> str:
        """Standalone HTML with ECharts CDN and inline data.

        chart_type: auto | sunburst | treemap | sankey | graph | bar | dashboard
        `dashboard` renders all applicable views side-by-side.
        """
        if chart_type == "auto":
            chart_type = self._auto_chart_type()

        # Pre-build every dataset the client might need — cheap and lets us
        # ship "dashboard" mode without extra work.
        hier = self._to_hierarchy(min_count=min_count, max_children=top_n)
        nodes, links = self._to_edges_nodes(top_n=top_n, min_count=min_count) \
            if len(self.dimensions) >= 2 else ([], [])
        bar_x, bar_y = self._to_bar(top_n=top_n)

        payload = {
            "hierarchy": hier,
            "nodes": nodes,
            "links": links,
            "bar_x": bar_x,
            "bar_y": bar_y,
            "dimensions": list(self.dimensions),
            "measures": [m["name"] for m in self.measures],
            "chart_type": chart_type,
            "title": title,
        }
        return _echarts_html(payload)

    def format_xml(self) -> str:
        """Generic XML dump of the cube (structure-agnostic)."""
        def esc(s: str) -> str:
            return (s.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))

        def emit(node, name, depth):
            pad = "  " * depth
            if isinstance(node, dict):
                meta = node.get("_meta", {})
                cnt = meta.get("count", 0) if isinstance(meta, dict) else 0
                attrs = f' count="{cnt}"' if cnt else ""
                # scalar measures as attributes
                for k, v in node.items():
                    if k.startswith("_") or isinstance(v, dict):
                        continue
                    attrs += f' {k}="{esc(str(v))}"'
                lines = [f"{pad}<{name}{attrs}>"]
                for k, v in node.items():
                    if k.startswith("_") or not isinstance(v, dict):
                        continue
                    lines.append(emit(v, f"item key=\"{esc(str(k))}\"", depth + 1))
                lines.append(f"{pad}</{name.split()[0]}>")
                return "\n".join(lines)
            return f"{pad}<{name}>{esc(str(node))}</{name.split()[0]}>"

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + emit(self.data, "cube", 0)

    def format_dot(self, top_n=None, min_count=None) -> str:
        """GraphViz DOT: expects exactly two dimensions treated as (src, dst).

        Emits a `digraph`; edge weight = leaf count. Nodes are auto-declared.
        """
        if len(self.dimensions) < 2:
            return "// dot output requires at least 2 dimensions (src, dst)"
        lines = ["digraph G {",
                 "  rankdir=LR;",
                 "  node [shape=box, fontsize=10];"]
        edges: Dict[tuple, int] = {}

        def walk(node, path):
            children = [(k, v) for k, v in node.items()
                        if isinstance(v, dict) and k not in ("_meta", "_meta_avg")]
            if not children:
                if len(path) >= 2:
                    src, dst = str(path[0]), str(path[1])
                    cnt = node.get("_meta", {}).get("count", 0)
                    if min_count is None or cnt >= min_count:
                        edges[(src, dst)] = edges.get((src, dst), 0) + cnt
                return
            for k, v in children:
                walk(v, path + [k])

        walk(self.data, [])
        nodes = set()
        for (s, d) in edges:
            nodes.add(s); nodes.add(d)
        for n in sorted(nodes):
            safe = n.replace('"', '\\"')
            lines.append(f'  "{safe}";')
        ranked = sorted(edges.items(), key=lambda kv: -kv[1])
        if top_n is not None:
            ranked = ranked[:top_n]
        for (s, d), w in ranked:
            ss = s.replace('"', '\\"'); ds = d.replace('"', '\\"')
            lines.append(f'  "{ss}" -> "{ds}" [label="{w}", weight={w}];')
        lines.append("}")
        return "\n".join(lines)

    def format_yaml(self) -> str:
        if HAS_YAML:
            return yaml.safe_dump(self._as_plain(self.data), sort_keys=False,
                                  allow_unicode=True, default_flow_style=False)
        # fallback: minimal indented yaml
        def dump(d, indent=0):
            lines = []
            pad = "  " * indent
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, dict):
                        lines.append(f"{pad}{k}:")
                        lines.append(dump(v, indent + 1))
                    else:
                        lines.append(f"{pad}{k}: {v}")
            return "\n".join(l for l in lines if l)
        return dump(self._as_plain(self.data))

    @staticmethod
    def _as_plain(node):
        if isinstance(node, dict):
            return {k: OlapCube._as_plain(v) for k, v in node.items()
                    if k not in ("_meta_avg",)}
        return node

    def format_md_table(self, human_bytes=False, max_lines=None) -> str:
        """Markdown table with one row per leaf record."""
        cols = list(self.dimensions) + ["count"] + [m["name"] for m in self.measures]
        rows = ["| " + " | ".join(cols) + " |",
                "|" + "|".join(["---"] * len(cols)) + "|"]

        def walk(node, path):
            children = [(k, v) for k, v in node.items()
                        if isinstance(v, dict) and k not in ("_meta", "_meta_avg")]
            if not children:
                cnt = node.get("_meta", {}).get("count", 0)
                rolled = self._rollup(node)
                cells = list(path) + [str(cnt)]
                for m in self.measures:
                    v = rolled.get(m["name"], "")
                    if isinstance(v, float):
                        v = f"{v:.3f}"
                    cells.append(str(v))
                rows.append("| " + " | ".join(cells) + " |")
                return
            for k, v in children:
                walk(v, path + [str(k)])

        walk(self.data, [])
        if max_lines is not None and len(rows) - 2 > max_lines:
            truncated = len(rows) - 2 - max_lines
            rows = rows[:2 + max_lines] + [f"| … | +{truncated} more |" + " |" * (len(cols) - 2)]
        return "\n".join(rows)


ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"


def _echarts_html(payload: Dict) -> str:
    """Build a standalone HTML document that renders the cube via ECharts.

    Multiple chart types are shipped inline; user picks via top-nav.  The
    `chart_type` field in payload seeds the initial view.
    """
    import json as _json
    data_json = _json.dumps(payload, ensure_ascii=False, default=str)
    title = payload["title"].replace("<", "&lt;")
    dims_label = " × ".join(payload["dimensions"]) or "—"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>cubest · {title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="{ECHARTS_CDN}"></script>
<style>
  html,body {{ margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; background:#fafafa; color:#222; }}
  header {{ padding:10px 16px; background:#1f2937; color:#f9fafb; display:flex; align-items:center; gap:16px; flex-wrap:wrap; }}
  header h1 {{ font-size:15px; margin:0; font-weight:600; }}
  header .dims {{ font-size:12px; opacity:.8; }}
  nav {{ margin-left:auto; display:flex; gap:6px; flex-wrap:wrap; }}
  nav button {{ background:#374151; color:#f9fafb; border:none; padding:6px 12px; border-radius:4px; font-size:13px; cursor:pointer; }}
  nav button.active {{ background:#3b82f6; }}
  nav button:disabled {{ opacity:.35; cursor:not-allowed; }}
  #chart {{ width:100vw; height:calc(100vh - 48px); }}
  footer {{ position:fixed; bottom:6px; right:12px; font-size:11px; color:#9ca3af; }}
</style>
</head>
<body>
<header>
  <h1>cubest · {title}</h1>
  <span class="dims">dimensions: {dims_label}</span>
  <nav id="nav"></nav>
</header>
<div id="chart"></div>
<footer>rendered offline · data embedded · <a href="https://echarts.apache.org/" style="color:#9ca3af">Apache ECharts 5</a></footer>
<script>
const PAYLOAD = {data_json};
const el = document.getElementById('chart');
const chart = echarts.init(el);
window.addEventListener('resize', () => chart.resize());

const AVAIL = {{
  sunburst: PAYLOAD.hierarchy.length > 0 && PAYLOAD.dimensions.length >= 2,
  tree:     PAYLOAD.hierarchy.length > 0,
  treemap:  PAYLOAD.hierarchy.length > 0,
  sankey:   PAYLOAD.links.length > 0,
  graph:    PAYLOAD.links.length > 0,
  bar:      PAYLOAD.bar_x.length > 0,
}};

function optSunburst() {{
  return {{
    tooltip: {{ trigger: 'item', formatter: '{{b}}<br/>value: {{c}}' }},
    series: [{{
      type: 'sunburst',
      data: PAYLOAD.hierarchy,
      radius: [0, '95%'],
      sort: (a, b) => (b.value||0) - (a.value||0),
      label: {{ rotate: 'radial', minAngle: 5 }},
      levels: [{{}}, {{itemStyle:{{borderWidth:2}}}}, {{itemStyle:{{borderWidth:1}}}}, {{itemStyle:{{borderWidth:1}}}}],
      emphasis: {{ focus: 'ancestor' }},
    }}]
  }};
}}

function optTreemap() {{
  return {{
    tooltip: {{ trigger: 'item', formatter: p => `${{p.treePathInfo.map(n=>n.name).join(' › ')}}<br/>value: ${{p.value}}` }},
    series: [{{
      type: 'treemap',
      data: PAYLOAD.hierarchy,
      leafDepth: 3,
      roam: true,
      breadcrumb: {{ show: true }},
      label: {{ show: true, formatter: '{{b}}' }},
      upperLabel: {{ show: true, height: 20 }},
      levels: [
        {{ itemStyle: {{ borderColor:'#fff', borderWidth:2, gapWidth:2 }} }},
        {{ itemStyle: {{ borderColor:'#e5e7eb', borderWidth:1, gapWidth:1 }} }},
        {{ colorSaturation: [0.35, 0.6], itemStyle:{{ borderWidth:1, gapWidth:1 }} }},
      ],
    }}]
  }};
}}

function optSankey() {{
  return {{
    tooltip: {{ trigger: 'item' }},
    series: [{{
      type: 'sankey',
      data: PAYLOAD.nodes,
      links: PAYLOAD.links,
      emphasis: {{ focus: 'adjacency' }},
      lineStyle: {{ color: 'gradient', curveness: 0.5 }},
      label: {{ fontSize: 11 }},
      nodeAlign: 'left',
    }}]
  }};
}}

function optGraph() {{
  const nodes = PAYLOAD.nodes.map(n => ({{
    name: n.name,
    symbolSize: 10 + Math.min(40, (PAYLOAD.links.filter(l => l.source===n.name || l.target===n.name).length)*2),
    draggable: true,
    label: {{ show: true, fontSize: 10 }},
  }}));
  return {{
    tooltip: {{ trigger: 'item' }},
    series: [{{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: PAYLOAD.links,
      roam: true,
      force: {{ repulsion: 220, edgeLength: 90, gravity: 0.05 }},
      lineStyle: {{ curveness: 0.15, opacity: 0.65 }},
      emphasis: {{ focus: 'adjacency' }},
    }}]
  }};
}}

function optBar() {{
  return {{
    tooltip: {{ trigger: 'axis' }},
    grid: {{ left: 60, right: 30, top: 20, bottom: 100 }},
    xAxis: {{ type: 'category', data: PAYLOAD.bar_x, axisLabel: {{ rotate: 40, interval: 0 }} }},
    yAxis: {{ type: 'value' }},
    series: [{{ type: 'bar', data: PAYLOAD.bar_y, itemStyle: {{ color: '#3b82f6' }} }}],
  }};
}}

function optTree() {{
  // ECharts `tree` expects a single root — wrap the hierarchy under a synthetic node.
  const roots = PAYLOAD.hierarchy;
  const root = roots.length === 1 ? roots[0] : {{ name: PAYLOAD.title || 'root', children: roots }};
  return {{
    tooltip: {{ trigger: 'item', formatter: '{{b}}<br/>value: {{c}}' }},
    series: [{{
      type: 'tree',
      data: [root],
      top: '2%', bottom: '2%', left: '10%', right: '15%',
      symbolSize: 8,
      orient: 'LR',
      layout: 'orthogonal',
      initialTreeDepth: 2,
      roam: true,
      expandAndCollapse: true,
      label: {{ position: 'left', verticalAlign: 'middle', align: 'right', fontSize: 11 }},
      leaves: {{ label: {{ position: 'right', verticalAlign: 'middle', align: 'left' }} }},
      emphasis: {{ focus: 'descendant' }},
    }}]
  }};
}}

const VIEWS = {{
  sunburst: {{ label: 'Sunburst', build: optSunburst }},
  tree:     {{ label: 'Tree',     build: optTree     }},
  treemap:  {{ label: 'Treemap',  build: optTreemap  }},
  sankey:   {{ label: 'Sankey',   build: optSankey   }},
  graph:    {{ label: 'Force graph', build: optGraph }},
  bar:      {{ label: 'Bar',      build: optBar      }},
}};

const nav = document.getElementById('nav');
Object.entries(VIEWS).forEach(([k, v]) => {{
  const b = document.createElement('button');
  b.textContent = v.label;
  b.dataset.type = k;
  b.disabled = !AVAIL[k];
  b.addEventListener('click', () => render(k));
  nav.appendChild(b);
}});

function render(type) {{
  chart.clear();
  chart.setOption(VIEWS[type].build());
  [...nav.querySelectorAll('button')].forEach(b => b.classList.toggle('active', b.dataset.type === type));
}}

let initial = PAYLOAD.chart_type;
if (!AVAIL[initial]) initial = Object.keys(AVAIL).find(k => AVAIL[k]) || 'bar';
render(initial);
</script>
</body>
</html>
"""


def _clip(lines: List[str], max_lines: Optional[int]) -> str:
    if not lines:
        return "(no data)"
    if max_lines is not None and len(lines) > max_lines:
        truncated = len(lines) - max_lines
        lines = lines[:max_lines] + [f"… (+{truncated} more)"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class Extractor:
    def __init__(self, rules: List[Dict]):
        self.rules = rules
        self._compiled: List[Any] = []
        for r in rules:
            rtype = r.get("type", "regex")
            if rtype == "regex":
                flags = 0
                if r.get("multiline", True):
                    flags |= re.MULTILINE
                if r.get("ignorecase", False):
                    flags |= re.IGNORECASE
                self._compiled.append(re.compile(r.get("pattern", ""), flags))
            elif rtype == "lines":
                self._compiled.append(re.compile(r.get("pattern", ".*")))
            else:
                self._compiled.append(None)

    def extract(self, content: str, filepath: str) -> List[Dict]:
        records: List[Dict] = []
        for rule, compiled in zip(self.rules, self._compiled):
            rtype = rule.get("type", "regex")
            if rtype == "regex":
                for m in compiled.finditer(content):
                    rec = {"_file": filepath, "_line": content[:m.start()].count("\n") + 1}
                    rec.update(m.groupdict())
                    _coerce(rec)
                    records.append(rec)
            elif rtype == "preset":
                records.extend(self._preset_content(rule, content, filepath))
            elif rtype == "lines":
                for i, line in enumerate(content.splitlines(), 1):
                    m = compiled.match(line)
                    if m:
                        rec = {"_file": filepath, "_line": i}
                        rec.update(m.groupdict())
                        _coerce(rec)
                        records.append(rec)
        return records

    def extract_line(self, line: str, filepath: str, lineno: int) -> List[Dict]:
        records: List[Dict] = []
        for rule, compiled in zip(self.rules, self._compiled):
            rtype = rule.get("type", "regex")
            if rtype == "regex":
                for m in compiled.finditer(line):
                    rec = {"_file": filepath, "_line": lineno}
                    rec.update(m.groupdict())
                    _coerce(rec)
                    records.append(rec)
            elif rtype == "lines":
                m = compiled.match(line)
                if m:
                    rec = {"_file": filepath, "_line": lineno}
                    rec.update(m.groupdict())
                    _coerce(rec)
                    records.append(rec)
            elif rtype == "preset":
                preset = rule.get("preset", "lines")
                if preset == "paths":
                    if lineno == 0:
                        records.append(_path_record(filepath, rule))
                elif preset == "headers":
                    if line.startswith("#"):
                        level = len(line) - len(line.lstrip("#"))
                        records.append({"_file": filepath, "_line": lineno,
                                        "level": level,
                                        "title": line.lstrip("# ").strip()})
                elif preset == "lines":
                    p = Path(filepath)
                    stripped = line.strip()
                    records.append({"_file": filepath, "_line": lineno,
                                    "line": line, "length": len(line),
                                    "ext": p.suffix.lstrip("."),
                                    "top": p.parts[0] if len(p.parts) > 1 else "",
                                    "name": p.name,
                                    "blank": 1 if not stripped else 0,
                                    "comment": 1 if stripped.startswith(("#", "//", "--", "/*", "*")) else 0})
                elif preset == "funcs":
                    for rec in _extract_funcs(line, filepath):
                        rec["_line"] = lineno
                        records.append(rec)
                elif preset == "md_checklist":
                    m = re.match(r'^\s*-\s*\[([xX ])\]\s*(.*)', line)
                    if m:
                        state = "done" if m.group(1).strip().lower() == "x" else "todo"
                        records.append({"_file": filepath, "_line": lineno,
                                        "state": state, "title": m.group(2).strip()})
                # md_frontmatter is batch-only (needs whole file); silently ignored here.
        return records

    def _preset_content(self, rule: Dict, content: str, filepath: str) -> List[Dict]:
        preset = rule.get("preset", "lines")
        out: List[Dict] = []
        if preset == "paths":
            out.append(_path_record(filepath, rule))
        elif preset == "headers":
            for i, line in enumerate(content.splitlines(), 1):
                if line.startswith("#"):
                    level = len(line) - len(line.lstrip("#"))
                    out.append({"_file": filepath, "_line": i,
                                "level": level, "title": line.lstrip("# ").strip()})
        elif preset == "lines":
            p = Path(filepath)
            ext = p.suffix.lstrip(".")
            top = p.parts[0] if len(p.parts) > 1 else ""
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                out.append({"_file": filepath, "_line": i,
                            "line": line, "length": len(line),
                            "ext": ext, "top": top, "name": p.name,
                            "blank": 1 if not stripped else 0,
                            "comment": 1 if stripped.startswith(("#", "//", "--", "/*", "*")) else 0})
        elif preset == "funcs":
            out.extend(_extract_funcs(content, filepath))
        elif preset == "calls":
            out.extend(_extract_calls(content, filepath))
        elif preset == "md_checklist":
            for i, line in enumerate(content.splitlines(), 1):
                m = re.match(r'^\s*-\s*\[([xX ])\]\s*(.*)', line)
                if m:
                    state = "done" if m.group(1).strip().lower() == "x" else "todo"
                    out.append({"_file": filepath, "_line": i,
                                "state": state, "title": m.group(2).strip()})
        elif preset == "md_frontmatter":
            m = re.match(r'\A---\r?\n([\s\S]{0,8000}?)\r?\n---', content)
            if m:
                rec = {"_file": filepath, "_line": 1}
                for ln in m.group(1).splitlines():
                    km = re.match(r'^([a-zA-Z_][\w-]*)\s*:\s*(.+?)\s*$', ln)
                    if km:
                        rec[km.group(1).lower()] = km.group(2).strip('"\'')
                out.append(rec)
        elif preset in ("csv", "tsv"):
            out.extend(_extract_csv(content, filepath, rule, preset))
        elif preset == "html_meta":
            out.extend(_extract_html_meta(content, filepath))
        elif preset == "html_headings":
            out.extend(_extract_html_headings(content, filepath))
        elif preset == "sitemap":
            out.extend(_extract_sitemap(content, filepath))
        return out


# Language table for multi-language func detection. Each entry: (lang, regex,
# kind_group_or_literal, name_group). Regex matches on lstripped line.
_FUNC_PATTERNS = [
    (".py",   re.compile(r'^(?P<kind>async\s+def|def|class)\s+(?P<name>\w+)\s*[\(:]')),
    (".pyi",  re.compile(r'^(?P<kind>async\s+def|def|class)\s+(?P<name>\w+)\s*[\(:]')),
    (".js",   re.compile(r'^(?:export\s+(?:default\s+)?)?(?P<kind>async\s+function|function|class)\s+(?P<name>\w+)')),
    (".ts",   re.compile(r'^(?:export\s+(?:default\s+)?)?(?P<kind>async\s+function|function|class|interface|type|enum)\s+(?P<name>\w+)')),
    (".jsx",  re.compile(r'^(?:export\s+(?:default\s+)?)?(?P<kind>function|class|const|let|var)\s+(?P<name>[A-Z]\w*)')),
    (".tsx",  re.compile(r'^(?:export\s+(?:default\s+)?)?(?P<kind>function|class|const|let|var)\s+(?P<name>[A-Z]\w*)')),
    (".go",   re.compile(r'^(?P<kind>func|type|interface|struct)\s+(?:\([^)]*\)\s+)?(?P<name>\w+)')),
    (".rs",   re.compile(r'^(?:pub\s+)?(?P<kind>fn|struct|enum|trait|impl|type|mod)\s+(?P<name>\w+)')),
    (".java", re.compile(r'^(?:public|private|protected|static|final|\s)*(?P<kind>class|interface|enum|record|[\w<>\[\]]+)\s+(?P<name>\w+)\s*\(')),
    (".c",    re.compile(r'^(?:static\s+|inline\s+)*[\w\*\s]+?(?P<kind>\w+)?\s*\**\s*(?P<name>\w+)\s*\([^;]*\)\s*\{?$')),
    (".cpp",  re.compile(r'^(?:static\s+|inline\s+)*[\w:<>\*\s&]+?(?P<kind>\w+)?\s*\**\s*(?P<name>\w+)\s*\([^;]*\)\s*(?:const\s+)?\{?$')),
    (".rb",   re.compile(r'^(?P<kind>def|class|module)\s+(?P<name>[\w.:!?=]+)')),
    (".php",  re.compile(r'^(?:public\s+|private\s+|protected\s+|static\s+)*(?P<kind>function|class|interface|trait)\s+(?P<name>\w+)')),
    (".kt",   re.compile(r'^(?:internal\s+|public\s+|private\s+)?(?P<kind>fun|class|object|interface)\s+(?P<name>\w+)')),
    (".swift",re.compile(r'^(?:public\s+|private\s+|internal\s+)?(?P<kind>func|class|struct|enum|protocol)\s+(?P<name>\w+)')),
    (".sh",   re.compile(r'^(?:function\s+)?(?P<name>\w+)\s*\(\s*\)\s*\{')),  # kind implicit
]

_INDENT_LANGS = (".py", ".pyi")


def _extract_funcs(content: str, filepath: str) -> List[Dict]:
    ext = os.path.splitext(filepath)[1].lower()
    candidates = [rx for suf, rx in _FUNC_PATTERNS if suf == ext]
    if not candidates:
        # fallback for unknown extensions: python-style
        candidates = [_FUNC_PATTERNS[0][1]]

    out: List[Dict] = []
    stack: List[tuple] = []  # (indent, name)  — for python indent-based nesting
    py_like = ext in _INDENT_LANGS
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped:
            continue
        indent = len(line) - len(stripped)
        match = None
        for rx in candidates:
            match = rx.match(stripped)
            if match:
                break
        if not match:
            continue
        gd = match.groupdict()
        name = gd.get("name") or ""
        if not name:
            continue
        kind = gd.get("kind") or "func"
        if py_like:
            while stack and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1] if stack else ""
            depth = len(stack)
            stack.append((indent, name))
        else:
            parent = ""
            depth = 0
        out.append({
            "_file": filepath, "_line": i,
            "kind": kind.strip(), "name": name,
            "parent": parent, "depth": depth,
            "lang": ext.lstrip("."),
        })
    return out


def _extract_csv(content: str, filepath: str, rule: Dict, preset: str) -> List[Dict]:
    """Parse CSV/TSV using stdlib csv. Header row → field names.

    Rule options:
      sep: ","  (auto ',' for csv / '\\t' for tsv)
      header: true|false|[explicit,fields]  — default true
      quotechar: '"'
      skip: 0                               — extra rows to drop
    """
    sep = rule.get("sep", "\t" if preset == "tsv" else ",")
    quote = rule.get("quotechar", '"')
    skip = int(rule.get("skip", 0))
    header_cfg = rule.get("header", True)

    reader = _csv_lib.reader(io.StringIO(content), delimiter=sep, quotechar=quote)
    rows = iter(reader)
    for _ in range(skip):
        try:
            next(rows)
        except StopIteration:
            return []

    if header_cfg is True:
        try:
            raw_headers = next(rows)
        except StopIteration:
            return []
        headers = [_slug(h) for h in raw_headers]
        start_line = 2 + skip
    elif isinstance(header_cfg, list):
        headers = [_slug(h) for h in header_cfg]
        start_line = 1 + skip
    else:
        # No header — use col_0, col_1, ...
        first = None
        try:
            first = next(rows)
        except StopIteration:
            return []
        headers = [f"col_{i}" for i in range(len(first))]
        # need to inject `first` back
        rows = _chain_iter([first], rows)
        start_line = 1 + skip

    out: List[Dict] = []
    for i, row in enumerate(rows, start_line):
        if not row:
            continue
        rec = {"_file": filepath, "_line": i}
        for h, v in zip(headers, row):
            rec[h] = v
        _coerce(rec)
        out.append(rec)
    return out


def _slug(s: str) -> str:
    """Column-name normaliser: strip, lowercase, non-alnum → _."""
    s = s.strip().lower()
    return re.sub(r'[^a-z0-9_]+', '_', s).strip('_') or "col"


def _chain_iter(*iters):
    for it in iters:
        for x in it:
            yield x


# ---------------- SEO / HTML / sitemap extractors ----------------
_TAG_STRIP = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _text(html_fragment: str, limit: int = 300) -> str:
    txt = _TAG_STRIP.sub(" ", html_fragment or "")
    txt = _WS_RE.sub(" ", txt).strip()
    return txt[:limit]


def _extract_html_meta(content: str, filepath: str) -> List[Dict]:
    """Return one record per HTML file with SEO-relevant meta fields.

    Fields: title, description, keywords, canonical, robots,
    h1_count, h1_first, h2_count, og_title, og_description,
    twitter_card, lang, has_schema (JSON-LD).
    """
    rec: Dict[str, Any] = {"_file": filepath, "_line": 1}
    m = re.search(r"<title[^>]*>(.*?)</title>", content, re.I | re.S)
    rec["title"] = _text(m.group(1)) if m else ""
    rec["title_len"] = len(rec["title"])

    def meta(name_attr: str, name_val: str) -> str:
        pat = rf'<meta\s+[^>]*{name_attr}\s*=\s*["\']{re.escape(name_val)}["\'][^>]*content\s*=\s*["\'](?P<v>[^"\']*)'
        m = re.search(pat, content, re.I)
        if m:
            return _text(m.group("v"), 500)
        pat2 = rf'<meta\s+[^>]*content\s*=\s*["\'](?P<v>[^"\']*)["\'][^>]*{name_attr}\s*=\s*["\']{re.escape(name_val)}'
        m = re.search(pat2, content, re.I)
        return _text(m.group("v"), 500) if m else ""

    rec["description"] = meta("name", "description")
    rec["desc_len"] = len(rec["description"])
    rec["keywords"] = meta("name", "keywords")
    rec["robots"] = meta("name", "robots")
    rec["og_title"] = meta("property", "og:title")
    rec["og_description"] = meta("property", "og:description")
    rec["twitter_card"] = meta("name", "twitter:card")

    m = re.search(r'<link\s+[^>]*rel\s*=\s*["\']canonical["\'][^>]*href\s*=\s*["\']([^"\']+)', content, re.I)
    rec["canonical"] = m.group(1) if m else ""

    m = re.search(r'<html\s+[^>]*lang\s*=\s*["\']([^"\']+)', content, re.I)
    rec["lang"] = m.group(1) if m else ""

    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", content, re.I | re.S)
    rec["h1_count"] = len(h1s)
    rec["h1_first"] = _text(h1s[0]) if h1s else ""
    rec["h2_count"] = len(re.findall(r"<h2[^>]*>", content, re.I))
    rec["h3_count"] = len(re.findall(r"<h3[^>]*>", content, re.I))
    rec["has_schema"] = 1 if 'application/ld+json' in content.lower() else 0

    return [rec]


def _extract_html_headings(content: str, filepath: str) -> List[Dict]:
    """Emit one record per heading with `level` (1..6), `title`, `_file`."""
    out: List[Dict] = []
    for m in re.finditer(r"<h(?P<level>[1-6])[^>]*>(?P<body>.*?)</h(?P=level)>",
                        content, re.I | re.S):
        out.append({
            "_file": filepath, "_line": content[:m.start()].count("\n") + 1,
            "level": int(m.group("level")),
            "title": _text(m.group("body")),
        })
    return out


def _extract_sitemap(content: str, filepath: str) -> List[Dict]:
    """Parse sitemap.xml (single or index): one record per <url>/<sitemap>."""
    out: List[Dict] = []
    for m in re.finditer(r"<url>(?P<body>.*?)</url>", content, re.I | re.S):
        body = m.group("body")
        loc = re.search(r"<loc>(.*?)</loc>", body, re.I | re.S)
        pri = re.search(r"<priority>(.*?)</priority>", body, re.I | re.S)
        lm = re.search(r"<lastmod>(.*?)</lastmod>", body, re.I | re.S)
        chg = re.search(r"<changefreq>(.*?)</changefreq>", body, re.I | re.S)
        url = _text(loc.group(1)) if loc else ""
        try:
            path = re.sub(r"^https?://[^/]+", "", url)
        except Exception:
            path = url
        parts = [p for p in path.split("/") if p]
        rec = {
            "_file": filepath,
            "_line": content[:m.start()].count("\n") + 1,
            "url": url,
            "path": path,
            "host": (re.match(r"https?://([^/]+)", url) or [None, ""])[1] if url else "",
            "priority": _text(pri.group(1)) if pri else "",
            "lastmod": _text(lm.group(1)) if lm else "",
            "changefreq": _text(chg.group(1)) if chg else "",
            "depth": len(parts),
            "section_1": parts[0] if len(parts) >= 1 else "",
            "section_2": parts[1] if len(parts) >= 2 else "",
            "section_3": parts[2] if len(parts) >= 3 else "",
        }
        _coerce(rec)
        out.append(rec)
    if not out:
        # sitemap-index case
        for m in re.finditer(r"<sitemap>(?P<body>.*?)</sitemap>", content, re.I | re.S):
            loc = re.search(r"<loc>(.*?)</loc>", m.group("body"), re.I | re.S)
            if loc:
                out.append({"_file": filepath,
                            "_line": content[:m.start()].count("\n") + 1,
                            "url": _text(loc.group(1)), "kind": "index"})
    return out


_CALL_RE = re.compile(r'\b(?P<callee>[A-Za-z_][\w]*)\s*\(')
_CALL_STOPWORDS = {
    "if", "for", "while", "return", "print", "yield", "raise", "with",
    "assert", "elif", "not", "and", "or", "in", "is", "lambda", "await",
    "async", "def", "class", "self", "cls", "super", "int", "str", "float",
    "list", "dict", "set", "tuple", "bool", "range", "len", "type",
    "isinstance", "getattr", "setattr", "hasattr", "print", "open",
    "function", "var", "let", "const", "new", "typeof", "instanceof",
}


def _extract_calls(content: str, filepath: str) -> List[Dict]:
    """For python-like sources: emit (caller → callee) pairs based on indent
    stack. Skips built-in-ish tokens to reduce noise. Best-effort — for
    exact analysis use tree-sitter-based tools (e.g. Graphify)."""
    ext = os.path.splitext(filepath)[1].lower()
    py_like = ext in _INDENT_LANGS
    out: List[Dict] = []
    stack: List[tuple] = []  # (indent, name)
    current_caller = ""
    def_re = re.compile(r'^(?:async\s+def|def|class)\s+(?P<name>\w+)\s*[\(:]')

    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        indent = len(line) - len(stripped)
        if py_like:
            while stack and stack[-1][0] >= indent:
                stack.pop()
            current_caller = stack[-1][1] if stack else "<module>"
            dm = def_re.match(stripped)
            if dm:
                stack.append((indent, dm.group("name")))
                current_caller = dm.group("name")
                continue
        else:
            dm = def_re.match(stripped)
            if dm:
                current_caller = dm.group("name")
                continue
        for cm in _CALL_RE.finditer(stripped):
            callee = cm.group("callee")
            if callee in _CALL_STOPWORDS:
                continue
            out.append({"_file": filepath, "_line": i,
                        "caller": current_caller or "<module>",
                        "callee": callee, "lang": ext.lstrip(".")})
    return out


def _path_record(filepath: str, rule: Dict) -> Dict:
    p = Path(filepath)
    parts = p.parts
    parent = str(p.parent).replace(os.sep, "/")
    if parent in ("", "."):
        parent = "/"
    abspath = rule.get("_abspath", filepath)
    try:
        size = os.path.getsize(abspath)
    except OSError:
        size = 0
    rec = {
        "_file": filepath, "_line": 0,
        "dir": parent, "basename": p.stem, "name": p.name,
        "ext": p.suffix.lstrip("."),
        "depth": len(parts) - 1,
        "top": parts[0] if len(parts) > 1 else "",
        "size": size,
    }
    # path prefixes for depth-N grouping (path_1 = "a", path_2 = "a/b", ...)
    # Only directory prefixes; the file itself is excluded.
    dir_parts = parts[:-1]
    for i in range(1, 6):
        rec[f"path_{i}"] = "/".join(dir_parts[:i]) if len(dir_parts) >= i else ""
    return rec


def _coerce(rec: Dict):
    for k, v in list(rec.items()):
        if isinstance(v, str):
            if v.isdigit() or (v.startswith("-") and v[1:].isdigit()):
                rec[k] = int(v)
            elif re.match(r'^-?\d+\.\d+$', v):
                rec[k] = float(v)


def _num(v):
    if isinstance(v, (int, float)):
        return v
    try:
        s = str(v)
        return float(s) if "." in s else int(s)
    except (ValueError, TypeError):
        return 0


def _hbytes(n: float) -> str:
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024:
            return f"{int(n)}B" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PiB"


def _csv(v: str) -> str:
    s = str(v)
    if any(c in s for c in ',"\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


# ---------------------------------------------------------------------------
# Scan / filtering
# ---------------------------------------------------------------------------

def _match_pattern(rel: str, name: str, pattern: str) -> bool:
    if not pattern:
        return False
    if pattern.startswith("/"):
        pat = pattern[1:]
        return fnmatch(rel, pat) or rel == pat
    if pattern.endswith("/"):
        dp = pattern[:-1]
        segs = rel.split("/")
        return any(fnmatch(seg, dp) for seg in segs[:-1]) if len(segs) > 1 else False
    if "**" in pattern:
        collapsed = re.sub(r"\*\*/?", "*", pattern)
        if fnmatch(rel, collapsed):
            return True
    if fnmatch(name, pattern):
        return True
    if "/" in pattern and fnmatch(rel, pattern):
        return True
    return pattern in rel


def _split_patterns(patterns: List[str]):
    positive, negated = [], []
    for p in patterns:
        if not p:
            continue
        if p.startswith("!"):
            negated.append(p[1:])
        else:
            positive.append(p)
    return positive, negated


def should_scan(path: Path, root: Path, include: List[str], exclude: List[str]) -> bool:
    try:
        rel = str(path.relative_to(root)).replace(os.sep, "/")
    except ValueError:
        rel = str(path).replace(os.sep, "/")
    name = path.name

    inc_pos, inc_neg = _split_patterns(include)
    exc_pos, exc_neg = _split_patterns(exclude)

    for e in exc_pos:
        if _match_pattern(rel, name, e):
            if any(_match_pattern(rel, name, n) for n in exc_neg):
                break
            return False

    if not inc_pos:
        return True
    for i in inc_pos:
        if _match_pattern(rel, name, i):
            if any(_match_pattern(rel, name, n) for n in inc_neg):
                return False
            return True
    return False


def dir_pruned(dirpath: Path, root: Path, exclude: List[str]) -> bool:
    try:
        rel = str(dirpath.relative_to(root)).replace(os.sep, "/")
    except ValueError:
        return False
    name = dirpath.name
    exc_pos, exc_neg = _split_patterns(exclude)
    if exc_neg:
        return False
    for e in exc_pos:
        if e.endswith("/"):
            if fnmatch(name, e[:-1]):
                return True
        elif "/" not in e and not any(c in e for c in "*?["):
            if name == e:
                return True
        elif _match_pattern(rel + "/", name, e):
            return True
    return False


# ---------------------------------------------------------------------------
# File IO
# ---------------------------------------------------------------------------

STREAM_THRESHOLD = 10 * 1024 * 1024  # 10 MiB


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8", errors="ignore")
    return open(path, mode="r", encoding="utf-8", errors="ignore")


def should_stream(path: Path, forced: Optional[bool]) -> bool:
    if forced is not None:
        return forced
    if path.suffix == ".gz":
        return True
    try:
        return path.stat().st_size > STREAM_THRESHOLD
    except OSError:
        return False


def iter_files(root: Path, include: List[str], exclude: List[str],
               files_from: Optional[Iterable[str]] = None) -> Iterable[Path]:
    if files_from is not None:
        # Explicit file list — used for MR/PR workflows via `git diff --name-only`.
        for raw in files_from:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            p = Path(raw)
            if not p.is_absolute():
                p = root / p
            if p.is_file() and should_scan(p, root, include, exclude):
                yield p
        return
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        dirnames[:] = sorted(
            d for d in dirnames if not dir_pruned(dp / d, root, exclude)
        )
        for fname in sorted(filenames):
            path = dp / fname
            if should_scan(path, root, include, exclude):
                yield path


def content_ok(path: Path, must, must_not, sample_bytes: Optional[int]) -> bool:
    """Check that file contents satisfy must-have / must-not regexes."""
    if not must and not must_not:
        return True
    try:
        with open_text(path) as fh:
            data = fh.read(sample_bytes) if sample_bytes else fh.read()
    except Exception:
        return False
    for p in must:
        if not p.search(data):
            return False
    for p in must_not:
        if p.search(data):
            return False
    return True


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

_SAFE_BUILTINS = {
    "len": len, "min": min, "max": max, "abs": abs, "int": int,
    "float": float, "str": str, "bool": bool, "any": any, "all": all,
    "sum": sum, "sorted": sorted, "round": round,
}


def passes_filters(record: Dict, filters: List[str]) -> bool:
    env = {k: v for k, v in record.items() if isinstance(v, (str, int, float, bool))}
    for expr in filters:
        try:
            if not eval(expr, {"__builtins__": _SAFE_BUILTINS}, env):
                return False
        except Exception:
            return False
    return True


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------

def load_profile(arg: str, profiles_dir: Path) -> Dict:
    if arg == "-":
        return parse_profile(sys.stdin.read())
    # If arg looks like inline JSON/YAML (starts with { or contains newline),
    # skip path lookup to avoid ENAMETOOLONG on giant one-liners.
    inline = arg.startswith("{") or "\n" in arg
    if not inline:
        for ext in (".yaml", ".yml", ".json", ""):
            built_in = profiles_dir / f"{arg}{ext}"
            try:
                if built_in.exists():
                    return parse_profile(built_in.read_text(encoding="utf-8"))
            except OSError:
                pass
        try:
            p = Path(arg)
            if p.exists():
                return parse_profile(p.read_text(encoding="utf-8"))
        except OSError:
            pass
    try:
        return json.loads(arg)
    except json.JSONDecodeError:
        pass
    if HAS_YAML:
        try:
            return yaml.safe_load(arg)
        except Exception:
            pass
    raise ValueError(f"Cannot parse profile: {arg[:120]}...")


def parse_profile(text: str) -> Dict:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    if HAS_YAML:
        return yaml.safe_load(text)
    raise RuntimeError("YAML not installed, but profile is not JSON")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(profile: Dict, root: Path):
    scanner = profile.get("scan", {})
    rules = profile.get("extract", [])
    extractor = Extractor(rules)
    cube = OlapCube(
        dimensions=profile.get("dimensions", ["_file"]),
        measures=profile.get("measures", [{"name": "count", "type": "count"}])
    )

    include = scanner.get("include", ["*"])
    exclude = scanner.get("exclude", [
        ".git/", "node_modules/", "__pycache__/", "*.pyc", ".claude/",
        "venv/", ".venv/", "*.lock", "dist/", "build/"
    ])
    stream_forced = scanner.get("stream")
    content_must = [re.compile(p) for p in scanner.get("content_match", [])]
    content_not = [re.compile(p) for p in scanner.get("content_not", [])]
    content_sample = scanner.get("content_scan_bytes")

    only_paths_preset = bool(rules) and all(
        r.get("type") == "preset" and r.get("preset") == "paths" for r in rules
    )
    has_csv_preset = any(
        r.get("type") == "preset" and r.get("preset") in ("csv", "tsv")
        for r in rules
    )
    if has_csv_preset:
        # CSV/TSV need the whole content in one shot (header parsing is stateful)
        stream_forced = False

    filters = profile.get("filters", [])
    root = root.resolve()
    file_count = 0
    record_count = 0

    files_from = profile.get("_files_from")
    for path in iter_files(root, include, exclude, files_from=files_from):
        if root.is_file() and path == root:
            rel = root.name
        else:
            try:
                rel = str(path.relative_to(root)).replace(os.sep, "/")
            except ValueError:
                rel = str(path)

        if (content_must or content_not) and not content_ok(
                path, content_must, content_not, content_sample):
            continue

        for r in rules:
            if r.get("type") == "preset" and r.get("preset") == "paths":
                r["_abspath"] = str(path)

        if only_paths_preset:
            file_count += 1
            for rec in extractor.extract("", rel):
                if passes_filters(rec, filters):
                    cube.add(rec)
                    record_count += 1
            continue

        stream = should_stream(path, stream_forced)
        try:
            if stream:
                with open_text(path) as fh:
                    file_count += 1
                    for i, line in enumerate(fh, 1):
                        line = line.rstrip("\n")
                        for rec in extractor.extract_line(line, rel, i):
                            if passes_filters(rec, filters):
                                cube.add(rec)
                                record_count += 1
            else:
                with open_text(path) as fh:
                    text = fh.read()
                file_count += 1
                for rec in extractor.extract(text, rel):
                    if passes_filters(rec, filters):
                        cube.add(rec)
                        record_count += 1
        except Exception as e:
            if profile.get("verbose"):
                print(f"# skip {rel}: {e}", file=sys.stderr)
            continue

    out = profile.get("output", {})
    fmt = out.get("format", "tree")
    top_n = out.get("top_n")
    min_count = out.get("min_count")
    human_bytes = bool(out.get("human_bytes", False))
    max_lines = out.get("max_lines")
    max_depth = out.get("max_depth")

    if fmt == "json":
        print(cube.format_json())
    elif fmt == "compact":
        print(cube.format_compact(max_lines=max_lines))
    elif fmt == "flat":
        print(cube.format_flat(top_n=top_n, min_count=min_count,
                               human_bytes=human_bytes, max_lines=max_lines))
    elif fmt == "csv":
        print(cube.format_csv(human_bytes=human_bytes, max_lines=max_lines))
    elif fmt in ("md", "md_table", "markdown"):
        print(cube.format_md_table(human_bytes=human_bytes, max_lines=max_lines))
    elif fmt in ("yaml", "yml"):
        print(cube.format_yaml())
    elif fmt in ("dot", "graphviz"):
        print(cube.format_dot(top_n=top_n, min_count=min_count))
    elif fmt in ("mermaid", "mmd"):
        print(cube.format_mermaid(top_n=top_n, min_count=min_count,
                                  direction=out.get("direction", "LR")))
    elif fmt in ("plantuml", "puml"):
        print(cube.format_plantuml(top_n=top_n, min_count=min_count))
    elif fmt in ("drawio", "diagrams"):
        print(cube.format_drawio(top_n=top_n, min_count=min_count))
    elif fmt == "xml":
        print(cube.format_xml())
    elif fmt in ("echarts", "html"):
        title = out.get("title") or profile.get("name") or "cubest"
        chart_type = out.get("chart_type", "auto")
        print(cube.format_echarts(chart_type=chart_type, title=title,
                                  top_n=top_n, min_count=min_count))
    else:
        print(cube.format_tree(top_n=top_n, min_count=min_count,
                               human_bytes=human_bytes, max_depth=max_depth,
                               max_lines=max_lines))

    if profile.get("verbose"):
        print(f"\n# scanned {file_count} files, {record_count} records",
              file=sys.stderr)


def get_profiles_dir() -> Path:
    script_dir = Path(__file__).parent.resolve()
    p = script_dir / "profiles"
    return p if p.exists() else script_dir


def diff_cubes(a_path: str, b_path: str) -> str:
    """Compare two cubest JSON outputs, print leaves that changed.

    Output: markdown table `path | before | after | delta`. Useful in CI
    to catch regressions like "TODO count grew on this PR".
    """
    a = json.loads(Path(a_path).read_text())
    b = json.loads(Path(b_path).read_text())

    def flatten(node, prefix=""):
        out = {}
        for k, v in node.items():
            if k in ("_meta", "_meta_avg") or not isinstance(v, dict):
                continue
            key = f"{prefix}>{k}" if prefix else str(k)
            has_children = any(
                isinstance(x, dict) and n not in ("_meta", "_meta_avg")
                for n, x in v.items()
            )
            if has_children:
                out.update(flatten(v, key))
            else:
                out[key] = v.get("_meta", {}).get("count", 0)
        return out

    fa, fb = flatten(a), flatten(b)
    keys = sorted(set(fa) | set(fb))
    lines = ["| path | before | after | delta |", "|---|---:|---:|---:|"]
    for k in keys:
        va, vb = fa.get(k, 0), fb.get(k, 0)
        if va != vb:
            lines.append(f"| {k} | {va} | {vb} | {vb-va:+d} |")
    return "\n".join(lines) if len(lines) > 2 else "no changes"


def main():
    parser = argparse.ArgumentParser(description="cubest — single-pass OLAP aggregator")
    parser.add_argument("--profile", "-p", default="file_tree",
                        help="Built-in name, path, inline JSON/YAML, or '-' for stdin")
    parser.add_argument("path", nargs="?", default=".",
                        help="Directory or single file (auto-detects .gz)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--files-from", "-F", default=None,
                        help="File with one path per line ('-' for stdin). "
                             "Ideal for MR/PR workflows: "
                             "`git diff --name-only origin/main | cubest -F - -p loc_counter`")
    parser.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"),
                        help="Compare two cubest JSON outputs — print leaves that "
                             "changed as a markdown table (for CI regressions).")
    args = parser.parse_args()

    if args.diff:
        print(diff_cubes(*args.diff))
        return

    profiles_dir = get_profiles_dir()
    try:
        profile = load_profile(args.profile, profiles_dir)
    except Exception as e:
        print(f"Error loading profile: {e}", file=sys.stderr)
        sys.exit(1)
    if args.verbose:
        profile["verbose"] = True
    if args.files_from:
        if args.files_from == "-":
            profile["_files_from"] = list(sys.stdin)
        else:
            profile["_files_from"] = Path(args.files_from).read_text().splitlines()
    run(profile, Path(args.path))


if __name__ == "__main__":
    main()
