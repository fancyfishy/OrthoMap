from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .loader import LanguageProfile, MappingFile
from .rules import Rule
from .apply import invert_rules


@dataclass
class Edge:
    src: str
    dst: str
    rules: List[Rule]
    forward: bool  # False表示这是通过reversible自动反向生成的边


def build_edges(profile: LanguageProfile) -> List[Edge]:
    edges: List[Edge] = []
    for m in profile.mappings:
        edges.append(Edge(m.node_a, m.node_b, m.rules, forward=True))
        if m.reversible:
            edges.append(Edge(m.node_b, m.node_a, invert_rules(m.rules), forward=False))
    return edges


def find_path(profile: LanguageProfile, src: str, dst: str) -> Optional[List[Edge]]:
    if src not in profile.nodes or dst not in profile.nodes:
        raise ValueError(f"节点不存在: {src} 或 {dst}（可用节点: {list(profile.nodes)}）")
    if src == dst:
        return []
    edges = build_edges(profile)
    adjacency: Dict[str, List[Edge]] = {}
    for e in edges:
        adjacency.setdefault(e.src, []).append(e)

    visited = {src}
    queue = deque([(src, [])])
    while queue:
        node, path = queue.popleft()
        for e in adjacency.get(node, []):
            if e.dst in visited:
                continue
            new_path = path + [e]
            if e.dst == dst:
                return new_path
            visited.add(e.dst)
            queue.append((e.dst, new_path))
    return None
