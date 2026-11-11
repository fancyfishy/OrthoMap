from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from typing import Dict, List

import yaml

from .rules import Rule, parse_ruleset


@dataclass
class NodeDef:
    node_id: str
    label: str
    inventory: List[str]


@dataclass
class MappingFile:
    node_a: str
    node_b: str
    reversible: bool
    rules: List[Rule]
    path: str


@dataclass
class LanguageProfile:
    code: str
    name: str
    description: str
    nodes: Dict[str, NodeDef]
    classes: Dict[str, List[str]]
    mappings: List[MappingFile] = field(default_factory=list)


def load_language(lang_dir: str) -> LanguageProfile:
    meta_path = os.path.join(lang_dir, "_meta.yaml")
    if not os.path.isfile(meta_path):
        raise FileNotFoundError(f"缺少主配置文件: {meta_path}")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    # nodes 按 _meta.yaml 里书写的顺序保留（约定：ipa -> phono -> ortho_1 -> ortho_2...），
    # 字典本身是有序的，这里不做任何重排，方便配置作者自己控制展示顺序。
    nodes: Dict[str, NodeDef] = {}
    for node_id, spec in (meta.get("nodes") or {}).items():
        nodes[node_id] = NodeDef(
            node_id=node_id,
            label=spec.get("label", node_id),
            inventory=spec.get("inventory") or [],
        )
    classes: Dict[str, List[str]] = meta.get("classes") or {}

    profile = LanguageProfile(
        code=meta.get("code", os.path.basename(lang_dir)),
        name=meta.get("name", os.path.basename(lang_dir)),
        description=meta.get("description", ""),
        nodes=nodes,
        classes=classes,
    )

    for path in sorted(glob.glob(os.path.join(lang_dir, "*.yaml"))):
        if os.path.basename(path) == "_meta.yaml":
            continue
        with open(path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        direction = doc.get("direction", "")
        if "->" not in direction:
            raise ValueError(f"{path}: direction 格式应为 'node_a -> node_b'，实际: {direction!r}")
        a, _, b = direction.partition("->")
        node_a, node_b = a.strip(), b.strip()
        for nid in (node_a, node_b):
            if nid not in nodes:
                raise ValueError(f"{path}: 节点 '{nid}' 未在 _meta.yaml 的 nodes 中定义")
        rules = parse_ruleset(doc.get("rules") or {})
        profile.mappings.append(MappingFile(
            node_a=node_a, node_b=node_b,
            reversible=bool(doc.get("reversible", False)),
            rules=rules, path=path,
        ))

    return profile


def discover_languages(languages_root: str) -> Dict[str, str]:
    """返回 {language_code: 目录路径}，扫描含 _meta.yaml 的子目录。"""
    out = {}
    for entry in sorted(os.listdir(languages_root)):
        full = os.path.join(languages_root, entry)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, "_meta.yaml")):
            out[entry] = full
    return out
