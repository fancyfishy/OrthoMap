# OrthoPhonoMap Engine v1.1

语言表示层映射引擎 —— 在正字法、音系转写、IPA 等表示层之间做规则驱动的转换。

## 项目结构

```
orthomap_1_1/
  core/
    engine.py       对外 API 入口：OrthoMapEngine.map(lang, src, dst, text)
    loader.py       读取 YAML 配置，构建 LanguageProfile
    graph.py        BFS 路径搜索（支持多跳自动串联）
    apply.py        规则应用（含反向推导辅助）
    rules.py        SPE 风格规则解析，支持多跳环境 before_seq/after_seq
    tokenizer.py    最长匹配分词
  cli/
    main.py         命令行前端
  languages/
    ja/             日语（训令式罗马字 / 平文式罗马字 → 音系转写 → IPA）
    gd/             苏格兰盖尔语（标准正字法 → 音系转写 → IPA）
  tests/
    test_engine.py  pytest 测试套件
```

## 快速开始

```bash
python cli/main.py
```

或作为库使用：

```python
from core.engine import OrthoMapEngine
eng = OrthoMapEngine("languages")
print(eng.map("ja", "ortho_1", "ipa", "tikara"))  # → tɕikara
print(eng.map("gd", "ortho_1", "ipa", "loch"))    # → l̪ˠɔx
```

## 配置格式（v1.1）

### _meta.yaml

```yaml
code: ja
name: "日语"
nodes:               # 节点默认顺序：ipa → phono → ortho_1 → ortho_2 → ...
  ipa:   {label: "IPA",      inventory: [...]}
  phono: {label: "音系转写", inventory: [...]}
  ortho_1: {label: "训令式罗马字", inventory: [...]}
classes:             # 命名类，规则里用 $name 引用
  vowels: [a, i, u, e, o]
```

### 映射文件（如 phono_to_ipa.yaml）

```yaml
direction: phono -> ipa
reversible: false
rules:
  t:
    - {to: tɕ, before: i}          # i 前腭化
    - {to: t}                       # elsewhere（无条件 = 兜底）
  n:
    - {to: m, before: [b, p, m]}   # 双唇音前同化（集合：OR 关系）
    - {to: n}
  a:
    - {to: au, before_seq: [[ll, m, nn], [$consonant_ortho, "#"]]}  # 多跳
    - {to: a}
```

**规则字段说明：**

| 字段 | 含义 |
|------|------|
| `to` | 目标音段（必填；`""` 表示删除）|
| `before` | 右侧紧邻条件（字面量 / `[a,b]` 集合 / `$class` / `"#"` 词尾）|
| `after` | 左侧紧邻条件（同上）|
| `not_before` | 右侧取反（不能和 `before` 同时出现）|
| `not_after` | 左侧取反（同上）|
| `before_seq` | 右侧多跳（列表，每项是一跳的条件）|
| `after_seq` | 左侧多跳（同上）|

无任何条件字段的条目 = `elsewhere`，应放在该 source 的变体列表最后。

## v1.1 主要变更

- 节点命名规范：`ipa` / `phono` / `ortho_1` / `ortho_2` ...（语言文件夹不再以正字法命名）
- 规则 DSL：从 SPE 字符串（`"t → tɕ / _i"`）改为嵌套 YAML 结构
- 多跳环境：新增 `before_seq` / `after_seq` 支持两步以上的邻居条件
- CLI：去掉"可用节点"预览，直接进编号选单
- 新增苏格兰盖尔语（`gd`）配置，覆盖辅音宽/窄变体和主要元音规则
