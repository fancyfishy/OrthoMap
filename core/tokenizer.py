"""按音段/字位清单做最长匹配(maximal munch)分词。未登录字符原样透传。"""
from __future__ import annotations

import re
from typing import List


def tokenize_word(word: str, inventory: List[str]) -> List[str]:
    inv_sorted = sorted(set(inventory), key=len, reverse=True)
    tokens: List[str] = []
    i = 0
    n = len(word)
    while i < n:
        matched = None
        for seg in inv_sorted:
            if seg and word.startswith(seg, i):
                matched = seg
                break
        if matched:
            tokens.append(matched)
            i += len(matched)
        else:
            tokens.append(word[i])  # 未登录字符：原样透传，长度按1推进
            i += 1
    return tokens


_WS_SPLIT = re.compile(r"(\s+)")


def tokenize_text(text: str, inventory: List[str]) -> List[str]:
    """返回按空白切分后的 word 列表结构在上层处理；这里只是单个 word 的便捷入口。"""
    return tokenize_word(text, inventory)


def split_words_keep_sep(text: str) -> List[str]:
    """保留分隔符的切词，用于词边界=空白的场景。"""
    return _WS_SPLIT.split(text)
