#!/usr/bin/env python3
"""orthomap CLI 前端，调用 core/engine.py。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.engine import OrthoMapEngine  # noqa: E402

LANGUAGES_ROOT = os.path.join(os.path.dirname(__file__), "..", "languages")


def choose(prompt: str, options: list) -> str:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(f"{prompt} [1-{len(options)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("输入无效，重试。")


def main():
    eng = OrthoMapEngine(LANGUAGES_ROOT)
    langs = eng.available_languages()
    if not langs:
        print(f"未在 {LANGUAGES_ROOT} 下找到任何语言配置。")
        return

    print("=== orthomap：多种正字法/音系转写/IPA映射工具 ===\n")
    print("可用语言：")
    lang_code = choose("选择语言", list(langs.keys()))
    profile = eng.load(lang_code)

    print(f"\n已加载: {profile.name}")
    if profile.description:
        print(f"  {profile.description.strip()}")

    node_ids = list(profile.nodes.keys())
    label_to_id = {profile.nodes[nid].label: nid for nid in node_ids}

    print()
    src_label = choose("源文本类型", list(label_to_id.keys()))
    src = label_to_id[src_label]

    dst_options = [lbl for lbl, nid in label_to_id.items() if nid != src]
    dst_label = choose("目标文本类型", dst_options)
    dst = label_to_id[dst_label]

    path = eng.describe_path(lang_code, src, dst)
    path_labels = [profile.nodes[nid].label for nid in path]

    print(f"\n映射路径: {' -> '.join(path_labels)}")
    print("输入文本进行转换（单击回车换行，双击回车提交，空着双击回车退出）：\n")

    while True:
        try:
            print(f"[{src_label}] > ", end="")
            
            lines = []

            while True:
                line = input()

                if not line:
                    break

                lines.append(line)

            if not lines:
                break

            text = "\n".join(lines)

        except (EOFError, KeyboardInterrupt):
            print()
            break

        try:
            result = eng.map(lang_code, src, dst, text)
            print(f"[{dst_label}] =\n{result}\n")
        except Exception as e:
            print(f"错误: {e}\n")


if __name__ == "__main__":
    main()