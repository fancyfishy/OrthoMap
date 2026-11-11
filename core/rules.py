"""
规则解析（v1.1：嵌套 YAML 结构，不再需要 SPE 箭头字符串）。

一个映射文件里的 `rules:` 字段长这样：

    rules:
      t:
        - {to: tɕ, before: i}
        - {to: t}                      # 没有任何 before/after = elsewhere，放最后
      n:
        - {to: m, before: [b, p, m]}   # 集合：命中其一即可，用 YAML 列表
        - {to: n}

每个 source 音段（比如上面的 "t"）下面挂一个变体列表，按写下的顺序尝试，
第一条条件满足的生效——跟 v1.0 的"文件内顺序、first-match-wins"语义完全一样，
只是不用再写箭头和 "X_Y" 这种字符串环境记法了。

每条变体支持的字段：
    to           目标音段（必填，允许空字符串 "" 表示"删除该音段"）
    before       右邻居条件（单跳）
    after        左邻居条件（单跳）
    not_before   右邻居条件取反（不能和 before 同时出现）
    not_after    左邻居条件取反（不能和 after 同时出现）
    before_seq   右侧多跳条件（列表，每一项是一跳；见下）
    after_seq    左侧多跳条件（列表，每一项是一跳；见下）

条件的值可以是：
    "i"              字面音段
    ["z", "c", "s"]  集合（命中其一即可）
    "$vowels"        引用 _meta.yaml 的 classes 里定义的命名类
    "#"              词边界

多跳环境（before_seq / after_seq）用于"看不止一个邻居"的情况，比如
苏格兰盖尔语"元音 + {ll,m,nn} + 辅音或词尾"这种要连续看两步的规则：

    a:
      - to: au
        before_seq:
          - [ll, m, nn]        # 第一跳：紧邻的右邻居
          - [$consonant, "#"]  # 第二跳：再往右一个位置
      - to: a

before_seq 每一项本身又可以是单个字面量、$class，或者 OR 列表——语法跟单跳的
before/after 完全一样，只是外面多包一层"第几跳"。not_before/not_after 目前只
支持单跳，多跳环境不支持取反（用 $class 排除法代替）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable


# ---------------------------------------------------------------------------
# natural class 展开（跟 v1.0 完全一样，没有变化）
# ---------------------------------------------------------------------------

def resolve_class(name: str, classes: Dict[str, List[str]], _seen: Optional[frozenset] = None) -> set:
    """展开命名类，支持类内引用其他 $class（带环检测）。

    _seen 记录的是"从根到当前节点"这一条路径上的祖先，每次递归传入一个新的
    frozenset（而不是共享同一个可变 set），这样两个兄弟分支各自引用同一个
    公共子类（菱形依赖，非环）时不会被误判为循环。
    """
    _seen = _seen or frozenset()
    if name in _seen:
        raise ValueError(f"natural class 循环引用: {name}")
    if name not in classes:
        raise ValueError(f"未定义的 natural class: ${name}")
    path = _seen | {name}
    out: set = set()
    for item in classes[name]:
        if isinstance(item, str) and item.startswith("$"):
            out |= resolve_class(item[1:], classes, path)
        else:
            out.add(item)
    return out


# ---------------------------------------------------------------------------
# 单个 hop（一跳邻居）的匹配
# ---------------------------------------------------------------------------

def _match_atom(neighbor: Optional[str], atom: str, classes: Dict[str, List[str]]) -> bool:
    """判断某一个具体邻居 token 是否命中一个"原子"条件（字面量 / $class / #）。"""
    if atom == "#":
        return neighbor is None
    if neighbor is None:
        return False
    if isinstance(atom, str) and atom.startswith("$"):
        return neighbor in resolve_class(atom[1:], classes)
    return neighbor == atom


def match_hop(neighbor: Optional[str], hop: Any, classes: Dict[str, List[str]]) -> bool:
    """判断某一跳的邻居是否命中该跳的条件。hop 可以是单个原子，
    也可以是一个 OR 列表（命中其一即可），列表元素同样可以是字面量/$class/#。"""
    if isinstance(hop, list):
        return any(_match_atom(neighbor, a, classes) for a in hop)
    return _match_atom(neighbor, hop, classes)


# ---------------------------------------------------------------------------
# Rule：一条"某 source 在某环境下变成某 target"的规则
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    source: str
    target: str
    left_hops: List[Any] = field(default_factory=list)   # 从近到远，[] = 不约束
    right_hops: List[Any] = field(default_factory=list)
    left_negated: bool = False   # 仅在 left_hops 长度为1时可能为 True（对应 not_after）
    right_negated: bool = False  # 仅在 right_hops 长度为1时可能为 True（对应 not_before）
    raw: str = ""                # 调试用的人类可读描述

    def context_matches(self, tokens: List[str], i: int, classes: Dict[str, List[str]]) -> bool:
        n = len(tokens)

        def neighbor_left(k: int) -> Optional[str]:
            idx = i - 1 - k
            return tokens[idx] if idx >= 0 else None

        def neighbor_right(k: int) -> Optional[str]:
            idx = i + 1 + k
            return tokens[idx] if idx < n else None

        l_ok = _side_matches(self.left_hops, self.left_negated, neighbor_left, classes)
        r_ok = _side_matches(self.right_hops, self.right_negated, neighbor_right, classes)
        return l_ok and r_ok


def _side_matches(hops: List[Any], negated: bool,
                   neighbor_fn: Callable[[int], Optional[str]],
                   classes: Dict[str, List[str]]) -> bool:
    if not hops:
        return True  # 没写 before/after = 不约束
    if negated:
        # 取反只可能来自 not_before/not_after，此时 hops 一定只有一跳。
        return not match_hop(neighbor_fn(0), hops[0], classes)
    for k, hop in enumerate(hops):
        if not match_hop(neighbor_fn(k), hop, classes):
            return False
    return True


# ---------------------------------------------------------------------------
# 从 YAML dict 解析出 Rule 列表
# ---------------------------------------------------------------------------

def _build_hops(single: Any, seq: Any, field_name: str) -> List[Any]:
    if single is not None and seq is not None:
        raise ValueError(f"{field_name}: 不能同时指定单跳和 _seq 多跳字段")
    if seq is not None:
        if not isinstance(seq, list):
            raise ValueError(f"{field_name}_seq 必须是列表（每一跳一项）")
        return list(seq)
    if single is not None:
        return [single]
    return []


def _describe(source: str, target: str, after, not_after, after_seq,
              before, not_before, before_seq) -> str:
    bits = []
    if after is not None:
        bits.append(f"after={after}")
    if not_after is not None:
        bits.append(f"not_after={not_after}")
    if after_seq is not None:
        bits.append(f"after_seq={after_seq}")
    if before is not None:
        bits.append(f"before={before}")
    if not_before is not None:
        bits.append(f"not_before={not_before}")
    if before_seq is not None:
        bits.append(f"before_seq={before_seq}")
    tail = " / " + ", ".join(bits) if bits else " / elsewhere"
    return f"{source} → {target!r}{tail}"


def _parse_variant(source: str, entry: Dict[str, Any]) -> Rule:
    if not isinstance(entry, dict) or "to" not in entry:
        raise ValueError(f"{source}: 每条规则必须是带 'to' 字段的映射，实际: {entry!r}")
    target = entry["to"]

    after, not_after, after_seq = entry.get("after"), entry.get("not_after"), entry.get("after_seq")
    before, not_before, before_seq = entry.get("before"), entry.get("not_before"), entry.get("before_seq")

    if not_after is not None and (after is not None or after_seq is not None):
        raise ValueError(f"{source}: not_after 不能和 after/after_seq 同时出现")
    if not_before is not None and (before is not None or before_seq is not None):
        raise ValueError(f"{source}: not_before 不能和 before/before_seq 同时出现")

    left_hops = _build_hops(not_after if not_after is not None else after, after_seq, f"{source}.after")
    right_hops = _build_hops(not_before if not_before is not None else before, before_seq, f"{source}.before")

    return Rule(
        source=source,
        target=target,
        left_hops=left_hops,
        right_hops=right_hops,
        left_negated=not_after is not None,
        right_negated=not_before is not None,
        raw=_describe(source, target, after, not_after, after_seq, before, not_before, before_seq),
    )


def parse_ruleset(raw_rules: Dict[str, List[Dict[str, Any]]]) -> List[Rule]:
    """把 `rules:` 整个 dict（source -> 变体列表）展开成 [Rule] 扁平列表。
    同一个 source 内部的顺序，就是 apply 阶段"第一条匹配的生效"所依赖的顺序。"""
    rules: List[Rule] = []
    for source, variants in (raw_rules or {}).items():
        if not variants:
            raise ValueError(f"{source}: 至少需要一条规则（哪怕只有一条 elsewhere）")
        for entry in variants:
            rules.append(_parse_variant(source, entry))
    return rules
