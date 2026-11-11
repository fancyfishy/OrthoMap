"""
orthomap engine对外核心 API。

用法示例:
    from orthomap.core.engine import OrthoMapEngine
    eng = OrthoMapEngine("languages")
    eng.map("cmn_pinyin", "orthography", "ipa", "si")
"""
from __future__ import annotations

import os
from typing import Dict, List

from .loader import LanguageProfile, load_language, discover_languages
from .graph import find_path
from .apply import apply_ruleset


class OrthoMapEngine:
    def __init__(self, languages_root: str):
        self.languages_root = languages_root
        self._cache: Dict[str, LanguageProfile] = {}

    def available_languages(self) -> Dict[str, str]:
        return discover_languages(self.languages_root)

    def load(self, lang_code: str) -> LanguageProfile:
        if lang_code not in self._cache:
            paths = self.available_languages()
            if lang_code not in paths:
                raise KeyError(f"未找到语言: {lang_code}（可用: {list(paths)}）")
            self._cache[lang_code] = load_language(paths[lang_code])
        return self._cache[lang_code]

    def nodes_of(self, lang_code: str) -> List[str]:
        return list(self.load(lang_code).nodes.keys())

    def map(self, lang_code: str, src_node: str, dst_node: str, text: str) -> str:
        profile = self.load(lang_code)
        path = find_path(profile, src_node, dst_node)
        if path is None:
            raise ValueError(f"[{lang_code}] 找不到从 '{src_node}' 到 '{dst_node}' 的映射路径")
        current_text = text.lower()
        current_node = src_node
        for edge in path:
            inventory = profile.nodes[current_node].inventory
            current_text = apply_ruleset(current_text, edge.rules, profile.classes, inventory)
            current_node = edge.dst
        return current_text

    def describe_path(self, lang_code: str, src_node: str, dst_node: str) -> List[str]:
        """返回映射链条上经过的节点序列，便于调试/展示给用户。"""
        profile = self.load(lang_code)
        path = find_path(profile, src_node, dst_node)
        if path is None:
            return []
        seq = [src_node] + [e.dst for e in path]
        return seq
