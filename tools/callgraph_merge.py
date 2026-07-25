#!/usr/bin/env python3
"""callgraph_merge.py — union multiple cubest JSON outputs into one DOT.

Typical workflow (3 runs, then one merge):

    # 1. calls per module/file — collect edges (caller → callee)
    for D in src/api src/core src/util; do
        python3 cubest.py --profile call_graph -p '{"...","output":{"format":"json"}}' "$D" \
            > /tmp/calls_$(basename $D).json
    done

    # 2. defined functions per module — collect nodes (so leafs get labelled
    #    even when they are never called elsewhere)
    python3 cubest.py -p '{
        "dimensions":["name"],
        "extract":[{"type":"preset","preset":"funcs"}],
        "output":{"format":"json"}}' src/ > /tmp/defs.json

    # 3. union
    python3 tools/callgraph_merge.py \
        --calls /tmp/calls_*.json \
        --defs  /tmp/defs.json \
        --out   /tmp/callgraph.dot

    # render
    dot -Tsvg /tmp/callgraph.dot > /tmp/callgraph.svg

The merger:
  - walks each JSON cube (dict of dicts) to extract leaf paths (as edges);
  - unions edge weights;
  - auto-declares every node — including those seen only in --defs — so the
    graph is complete even for uncalled symbols;
  - highlights sinks (in-degree > 0, out-degree = 0) and hubs (top-N by
    in+out degree).
"""

import argparse
import glob
import json
import sys
from pathlib import Path
from collections import defaultdict


def _walk_leaves(node, path=None, out=None):
    """Yield (path, count) for each leaf of a cubest cube dict."""
    if path is None:
        path = []
    if out is None:
        out = []
    children = [(k, v) for k, v in node.items()
                if isinstance(v, dict) and k not in ("_meta", "_meta_avg")]
    if not children:
        cnt = node.get("_meta", {}).get("count", 0)
        out.append((tuple(path), cnt))
        return out
    for k, v in children:
        _walk_leaves(v, path + [str(k)], out)
    return out


def load_edges(paths):
    edges = defaultdict(int)
    nodes = set()
    for p in paths:
        try:
            data = json.loads(Path(p).read_text())
        except Exception as e:
            print(f"skip {p}: {e}", file=sys.stderr)
            continue
        for path, cnt in _walk_leaves(data):
            if len(path) == 1:
                nodes.add(path[0])
            elif len(path) >= 2:
                s, d = path[0], path[1]
                edges[(s, d)] += cnt
                nodes.add(s); nodes.add(d)
    return edges, nodes


def render_dot(edges, nodes, top_edges=None, highlight_hubs=10):
    lines = [
        "digraph CallGraph {",
        "  rankdir=LR;",
        "  node [shape=box, fontsize=10, style=filled, fillcolor=\"#f5f5f5\"];",
        "  edge [fontsize=8, color=\"#666666\"];",
    ]
    in_deg = defaultdict(int)
    out_deg = defaultdict(int)
    for (s, d), w in edges.items():
        out_deg[s] += w
        in_deg[d] += w
    # rank hubs by total degree
    hubs = sorted(nodes, key=lambda n: -(in_deg[n] + out_deg[n]))[:highlight_hubs]
    hubs_set = set(hubs)

    for n in sorted(nodes):
        safe = n.replace('"', '\\"')
        if n in hubs_set:
            lines.append(f'  "{safe}" [fillcolor="#ffe08a"];')
        elif in_deg[n] > 0 and out_deg[n] == 0:
            lines.append(f'  "{safe}" [fillcolor="#c8e6c9"];')  # sink
        elif out_deg[n] > 0 and in_deg[n] == 0:
            lines.append(f'  "{safe}" [fillcolor="#bbdefb"];')  # entrypoint
        else:
            lines.append(f'  "{safe}";')

    ranked = sorted(edges.items(), key=lambda kv: -kv[1])
    if top_edges is not None:
        ranked = ranked[:top_edges]
    for (s, d), w in ranked:
        ss = s.replace('"', '\\"'); ds = d.replace('"', '\\"')
        lines.append(f'  "{ss}" -> "{ds}" [label="{w}", weight={w}];')

    lines.append("}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Merge cubest JSON outputs into a call-graph DOT")
    ap.add_argument("--calls", nargs="+", required=True,
                    help="JSON files with (caller, callee) leaves. Globs allowed.")
    ap.add_argument("--defs", nargs="*", default=[],
                    help="JSON files with single-dimension leaves = defined nodes.")
    ap.add_argument("--out", default="-", help="Output .dot path or '-' for stdout")
    ap.add_argument("--top-edges", type=int, default=500)
    ap.add_argument("--hubs", type=int, default=10)
    args = ap.parse_args()

    call_files, def_files = [], []
    for pat in args.calls:
        call_files.extend(sorted(glob.glob(pat)) or [pat])
    for pat in args.defs:
        def_files.extend(sorted(glob.glob(pat)) or [pat])

    edges, nodes = load_edges(call_files)
    _, extra_nodes = load_edges(def_files)
    nodes |= extra_nodes

    dot = render_dot(edges, nodes,
                     top_edges=args.top_edges, highlight_hubs=args.hubs)

    if args.out == "-":
        print(dot)
    else:
        Path(args.out).write_text(dot)
        print(f"wrote {args.out} ({len(nodes)} nodes, {len(edges)} edges)",
              file=sys.stderr)


if __name__ == "__main__":
    main()
