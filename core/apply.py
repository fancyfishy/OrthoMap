from __future__ import annotations

from typing import List, Dict
from .rules import Rule
from .tokenizer import tokenize_word, split_words_keep_sep


def apply_rules_to_word(tokens: List[str], rules: List[Rule], classes: Dict[str, List[str]]) -> List[str]:
    out: List[str] = []
    for i, tok in enumerate(tokens):
        output = tok  # 默认原样透传(未命中任何规则)
        for rule in rules:
            if rule.source == tok and rule.context_matches(tokens, i, classes):
                output = rule.target
                break
        out.append(output)
    return out


def apply_ruleset(text: str, rules: List[Rule], classes: Dict[str, List[str]],
                   src_inventory: List[str]) -> str:
    pieces = split_words_keep_sep(text)
    result_pieces: List[str] = []
    for piece in pieces:
        if piece == "" or piece.isspace():
            result_pieces.append(piece)
            continue
        tokens = tokenize_word(piece, src_inventory)
        out_tokens = apply_rules_to_word(tokens, rules, classes)
        result_pieces.append("".join(out_tokens))
    return "".join(result_pieces)


def invert_rules(rules: List[Rule]) -> List[Rule]:
    """粗略反向：交换 source/target，环境条件原样保留。

    警告（跟 v1.0 一样的限制，没有变化）：
    1) 当规则的环境在两个方向上不是1:1对应时（常见于条件变体坍缩，如
       多个 source 坍缩到同一个 target），反向结果不保证语言学正确。
    2) 环境条件（before/after）里的 token 是按"原方向"的邻居定义的，
       反向应用时邻居已经是目标层的表示——如果两层音段清单不重叠，
       这些环境条件可能永远匹配不上。
    engine 只会在该映射文件声明 reversible: true 时才会走这条路径，
    且更适合上下文无关的简单 1:1 替换规则。
    """
    inverted = []
    for r in rules:
        inverted.append(Rule(
            source=r.target, target=r.source,
            left_hops=r.left_hops, right_hops=r.right_hops,
            left_negated=r.left_negated, right_negated=r.right_negated,
            raw=f"(auto-inverted) {r.raw}",
        ))
    return inverted
