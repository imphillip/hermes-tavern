# SoulTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> 让任何带有 SOUL.md 的 agent runtime 都能换上你的 SillyTavern 角色卡。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

SoulTavern 是一次性导入工具，把 SillyTavern V2 角色卡
(`.png` / `.json`) 转成 agent runtime 启动时加载的 markdown
系统提示词文件。v2.0 内置两个可用 target：`--target hermes`（写出
[Hermes-Agent](https://github.com/NousResearch/hermes-agent) 用的
`SOUL.md` + `HERMES.md`）和 `--target openclaw`（写出
[OpenClaw](https://github.com/imphillip/openclaw) workspace 用的
`SOUL.md` + `AGENTS.md` managed-section + `IDENTITY.md`）。

不需要中间件、不打补丁、不做转发，**也不需要安装。** SoulTavern 就是
一个自包含的 skill 文件夹，零三方 Python 依赖。把文件夹丢到 runtime
读取 skill 的目录里，直接调脚本——结束。

**血脉:** `TavernAI` → `SillyTavern` → `HermesTavern` → **`SoulTavern`**

> SoulTavern v2.0 收敛为 skill-folder-only 分发。`soultavern` CLI（以及
> `hermes-tavern` 向后兼容别名）已经移除——所有操作都是
> `skills/soultavern/scripts/` 下的脚本。`--target hermes` 和
> `--target openclaw` 的输出与 v1.0 字节级一致；变化的只是调用方式。
> 迁移说明见 [CHANGELOG.md](CHANGELOG.md#200)。

---

## 愿景：从 HermesTavern 到 SoulTavern

HermesTavern 是更大方向上的第一个具体实例：让任何"会话开始时加载固定
人格文件"的 agent runtime，都有机会接入完整的 SillyTavern 角色卡生态。

**SoulTavern** 就是这个多目标版本的抽象。今天有两个生产可用的 target：
`--target hermes`（默认；输出 `SOUL.md` + `HERMES.md`）和
`--target openclaw`（输出 `SOUL.md` + `AGENTS.md` managed-section +
`IDENTITY.md`）。通用 `--target generic` 回退已注册为骨架，将在后续
版本完成。

### 三条原则

1. **以"灵魂可移植"为先，不追"功能完美"。** SillyTavern 和 RisuAI 是
   重度 RP 的归宿；SoulTavern 做的是单向移植——把社区已经做好的成千
   上万张 V2 角色卡，搬到那些原生不说 SillyTavern 协议的 agent
   runtime 上。损失的 30-40%（流式 token、swipe/regen/branch、
   关键词触发 lorebook 注入）属于 channel/UI 层的机制，我们刻意不追；
   能成功移植的 70-80% 已经够覆盖大部分轻度到中度 RP 场景。

2. **文件级适配是通用接口。** 任何"会话开始时加载 markdown 系统提示
   词文件"的 agent runtime 都可以做适配目标。适配分两层：(a) 把 V2
   字段渲染到该 runtime 对应的提示词文件（Hermes 是 `SOUL.md` +
   `HERMES.md`；OpenClaw 是 `SOUL.md` + `IDENTITY.md` +
   `AGENTS.md`），(b) 在 runtime 加载优先级最高的那份文件里注入
   **IDENTITY DIRECTIVE**（Hermes 是 SOUL.md，OpenClaw 是 AGENTS.md），
   压制该 runtime 默认的"我是 AI 助手"自我框架。(b) 是命门——压不
   住，agent 只是穿了件灵魂的衣服，本质还是它自己。

3. **工具做确定性工作，LLM 工作交给 agent。** Python 脚本不 shell
   out 调任何独立 LLM（v0.4.0 踩过这个坑，v0.4.5 改正了）。当卡片
   超过常驻上下文容量，`import.py` 把 `source.md` 摆到磁盘上、退出
   码 2；调用方 agent 在自己的上下文里用自己的文件工具做 V2 分类。
   这样工具不依赖 LLM CLI 的版本演化，agent 处理素材时的信任态度
   也跟它处理任何第三方文件一样——遇到与策略冲突的内容可以正大光明
   地拒绝，缺失会在索引里可见（这是诚实的信号，不是悄悄改写）。

---

## 怎么用

只要 runtime 知道 SoulTavern skill 文件夹在哪，整个用户面交互就是
对话式的。在 runtime 的聊天里上传角色卡文件，然后用大白话说你想干嘛：

> _[aldous.png 已附加]_ 安装这个角色

> 切换到 alice

> 把所有角色都忘掉，恢复成默认

就这些。runtime 解析意图，在背后调用对应的 SoulTavern 脚本，
变更准备好之后会主动告诉你开个新会话（Hermes 用 `/new` 或 `/reset`）
让它生效。有歧义的时候直接用大白话再说一句即可。

## 安装

**没有安装步骤。** SoulTavern 是一个 skill 文件夹，除 Python ≥ 3.10
之外没有任何运行时依赖。把文件夹丢到 runtime 读取 skill 的目录里就完事。

```bash
git clone https://github.com/imphillip/SoulTavern.git
cp -r SoulTavern/skills/soultavern <YOUR_RUNTIME_SKILLS_DIR>/
```

到此为止。runtime 那边的 agent 会读 `skills/soultavern/SKILL.md`，
按需调用 `python3 .../scripts/import.py` 等脚本。不动 PATH、不打 wheel、
不靠 `pipx`、没有全局状态。

`<YOUR_RUNTIME_SKILLS_DIR>` 取决于具体 runtime：典型情况是
`~/.openclaw/workspace/skills/`、Hermes 的 skills 目录、或者 Claude Code 的
`~/.claude/skills/`。任何 runtime 扫 skill 的目录都行。

### 或者通过 runtime 的 skill hub

如果你的 runtime 支持 hub-style "tap"（比如 Hermes）：

```bash
hermes skills tap add imphillip/SoulTavern
hermes skills install soultavern
```

hub 安装器只是把同一份 skill 文件夹放进去，没别的动作。

### 升级

用新版本覆盖 skill 文件夹：

```bash
git pull   # 在你的 SoulTavern checkout 里
cp -r SoulTavern/skills/soultavern <YOUR_RUNTIME_SKILLS_DIR>/
```

（hub 用户重新跑一次 `hermes skills install soultavern` 即可。）

skill 文件夹是纯静态的——里面没有任何运行时生成的状态会被覆盖踩坏。
已导入的卡、快照历史、已渲染的人格文件都在 `<home>` workspace 里，
跨升级不变。`.active.json` 的 schema 自 v1.0 起稳定，旧版本的
workspace 不需要任何迁移。

### 卸载

干净卸载的步骤取决于用过哪些 target。

**只用了 hermes target：** 直接删 skill 文件夹：

```bash
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
```

需要的话再清掉每个用过的 `HERMES_HOME` 下的人格文件和卡库：

```bash
rm -rf <HERMES_HOME>/{SOUL.md,HERMES.md,cards}
```

`SOUL.md` / `HERMES.md` / `cards/` 是 SoulTavern 写的，但属于
**用户内容**（人格 + 快照 + 卡片备份），所以归你决定要不要清。

**用了 openclaw target：** 删 skill 文件夹**之前**，先在每个用过的
workspace 跑一次 `delete.py`：

```bash
# 对每个用过 SoulTavern 的 openclaw workspace：
python3 <SKILL_DIR>/scripts/current.py --home <ws>          # 看一下当前 active 卡名
python3 <SKILL_DIR>/scripts/delete.py  --card <name> --home <ws>

# 然后再删 skill 文件夹：
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
```

原因：SoulTavern 在 workspace 的 `AGENTS.md` 里写了一段 managed
section（`<!-- BEGIN soultavern:character -->` 到对应 `END` 标记
之间的部分）。光删 skill 文件夹不会去除这一段——它会以纯 markdown
的形式赖在 `AGENTS.md` 里，每次新会话开始 runtime 都会把那段
IDENTITY DIRECTIVE 加载进去。对 active 卡跑 `delete.py` 会干净地
strip 掉这段 managed section、删掉 `IDENTITY.md` 和 `SOUL.md`，
同时保留 `AGENTS.md` marker 之外的用户内容。

如果不想跑 `delete.py`，也可以手工编辑每个 `AGENTS.md`，把
`<!-- BEGIN soultavern:character -->` 到 `<!-- END soultavern:character -->`
之间的所有内容（含 marker 本身）删干净。

`<ws>/cards/` 下的卡库（备份 + 快照）和 managed section 是独立
的，可以分开决定保留或清掉。

### 依赖

- Python ≥ 3.10（仅 stdlib——不再依赖 pillow / jinja2 / pyyaml）。
- 超大角色卡的处理由调用方 agent 自己完成（Hermes 本身，或者任何驱动
  导入流程的 agent）：脚本把 `source.md` 摆到磁盘上，agent 用自己的
  文件工具把内容分发到各类别文件。不再 shell out 到任何独立的 LLM CLI。

---

## 缘起

Hermes 启动时本来就会把 `SOUL.md`（独立身份槽）和 `HERMES.md`（cwd 相关的
项目上下文槽）自动加载进 system prompt。唯一缺的是一个尊重 SillyTavern V2
schema、占位符语法（`{{char}}`、`{{user}}`、`<BOT>`、`<USER>`）以及
lorebook 布局的转换器。SoulTavern 的 `--target hermes` 就是来补这一环的。

OpenClaw 的结构是同构的——`SOUL.md` + `AGENTS.md` + `IDENTITY.md` 都会被
读进会话开始时的 bootstrap 预算——只是加载优先级反过来（AGENTS.md 高于
SOUL.md，所以 IDENTITY DIRECTIVE 必须落在 AGENTS.md 里）。这就是
`--target openclaw`。

刻意不做的事：

- 改 runtime 源码
- 写中间件 / 转发层
- 碰渠道配置（`platform_toolsets`、白名单……）
- 启动或托管 runtime 进程
- 写 `MEMORY.md` / `USER.md` / `CLAUDE.md`
- 写 `AGENTS.md` 中 openclaw managed-section 标记之外的任何内容
  （`--target hermes` 完全不写 `AGENTS.md`；`--target openclaw` 只动
  marker 之间的那段，marker 之外的用户内容原样保留）

## 功能

- **V2 + V1 + PNG 解析**——SillyTavern 在野的 JSON / PNG 容器形态全收
  （v2.0 移除了 YAML 支持；生态里几乎没人用）
- **占位符替换**——`{{char}}` / `{{user}}` 加上老式的 `<BOT>` / `<USER>`，
  大小写不敏感、不递归
- **Lorebook 渲染**——按 `insertion_order` 排序，禁用条目跳过，
  超长尾部截断。Hermes target 写入 `HERMES.md`；OpenClaw target 写入
  `AGENTS.md` 的 managed section。
- **身份指令**——自动注入到当前 runtime 加载优先级最高的那份文件
  （Hermes 是 SOUL.md；OpenClaw 是 AGENTS.md），覆盖 runtime 内置的
  "你是 AI 助手"框架，让模型直接以角色身份回答，避免出现"我是 AI；
  如果是在角色扮演的话，我在饰演 X"这种回答。
- **三层安全**——可见的信任横幅、解析期消毒（零宽字符 / RTL 覆盖 /
  控制字符清理）、按提示注入类别做的红旗模式扫描
- **超大卡的 agent 驱动流程**——当卡片渲染后超过 runtime 单文件预算的
  阈值，`import.py` 把源素材摆到磁盘上，调用方 agent 在自己的上下文里
  把内容分发到 V2 类别（不再 shell out 到任何子进程 LLM）。之后由
  `finalize.py` 拼出精选 SOUL.md 和 companion 索引文件。
- **角色卡库**——对已导入到 `<home>` 目录（Hermes 是 `HERMES_HOME`，
  OpenClaw 是 workspace 目录）的卡做 list / current / switch /
  delete / restore
- **快照历史**——每次 `import` / `switch` / `revert` 都被捕获到
  `cards/.snapshots/`，还有一个特殊的 `pristine` 快照保存装卡前的原状。
  `revert --to pristine` / `--previous` / `--to <id|name>` 可以回溯历史
- **渠道无关**——产生的是 runtime 启动时加载的人格文件；
  runtime 能说话的所有地方都自动在角色里

## 常用命令

先设 `SKILL=path/to/skills/soultavern`，然后：

```bash
# 检查一张卡（解析 + 渲染 + 扫描，不写文件）
python3 $SKILL/scripts/validate.py --card aldous.png

# 预览渲染好的 markdown
python3 $SKILL/scripts/import.py --card aldous.png --home ~/.hermes-roleplay --dry-run

# 替换已存在的人格
python3 $SKILL/scripts/import.py --card alice.png --home ~/.hermes-roleplay --overwrite

# 卡库管理
python3 $SKILL/scripts/list.py    --home ~/.hermes-roleplay [--all]
python3 $SKILL/scripts/current.py --home ~/.hermes-roleplay
python3 $SKILL/scripts/switch.py  --card alice --home ~/.hermes-roleplay
python3 $SKILL/scripts/delete.py  --card bob   --home ~/.hermes-roleplay
python3 $SKILL/scripts/restore.py --card bob   --home ~/.hermes-roleplay

# 快照历史（每次 import/switch 都会捕获）
python3 $SKILL/scripts/history.py --home ~/.hermes-roleplay
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --to pristine
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --previous
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --to 0003

# 信任卡作者的 system_prompt / post_history_instructions
# （默认会渲染进不可信引用块里）
python3 $SKILL/scripts/import.py ... --trust-system-prompt

# agent 把超大卡的 extended/<category>.md 写完之后，跑这一步收尾
python3 $SKILL/scripts/finalize.py --card aldous --home ~/.hermes-roleplay
```

`switch` / `delete` / `restore` 接受文件名或角色名（对解析得到的 `name`
字段或文件名 stem 做大小写不敏感的前缀匹配）。

## 运行模式

SoulTavern 按渲染后的体积自动选择两种模式之一。阈值是 runtime 单文件
槽的 75%——`--target hermes` 是 15,000 字符，`--target openclaw` 是 9,000
字符（详见 `references/openclaw-target.md`）。

### 小卡（渲染输出在阈值之下）

`--target hermes` 布局：

```
<home>/
├── SOUL.md                          ← 渲染后的人格
├── HERMES.md                        ← 渲染后的 lorebook
│                                       (仅当卡有 character_book 时)
└── cards/
    ├── .active.json                 ← 当前激活卡的指针
    ├── .snapshots/<NNNN>_…/         ← 人格文件历史
    ├── .trash/                      ← 软删除的卡 (delete/restore)
    └── <name>_<ts>.<ext>            ← 原卡备份
```

`--target openclaw` 多写一份 `IDENTITY.md`（角色元数据），且 lorebook
是作为 managed section 写进 `AGENTS.md` 的，而不是单独的 `HERMES.md`。
逐文件细节见 `references/openclaw-target.md`。

### 超大卡—— agent 驱动

SoulTavern **不会** shell out 到任何独立 LLM。`import.py` 把源素材
摆到磁盘上、退出码 2，并提示调用方 agent 把内容分发到 8 个
V2 类别——忠于原文措辞，遇到与策略冲突的内容可以优雅地跳过。
agent 写完类别文件之后，跑 `finalize.py` 拼出最终的 SOUL.md
（精选几个常驻类别）和 companion 索引文件。

```
<home>/
├── SOUL.md                          ← 精选三类: identity + personality + roleplay_guides
├── <companion>                      ← 导演指令 + V2 类别索引
│                                       (HERMES.md 或 AGENTS.md managed section)
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← 原卡备份
    └── <name>_<ts>/
        ├── source.md                ← 脚本摆给 agent 的输入素材
        └── extended/                ← V2 类别
            ├── identity.md          ← 名字、年龄、种族、基本信息          (agent 写)
            ├── appearance.md        ← 外貌、体态、声音、特征               (agent 写)
            ├── personality.md       ← 性格、习惯、说话方式                  (agent 写)
            ├── backstory.md         ← 过往、历史、关系                       (agent 写)
            ├── scenario.md          ← 对话开场的设定                          (agent 写)
            ├── kinks.md             ← 偏好（仅源卡含此内容时生成）         (agent 写)
            ├── roleplay_guides.md   ← 显式角色扮演指引                       (agent 写)
            ├── examples.md          ← 示例对话                                  (agent 写)
            ├── alternate_greetings/01.md, 02.md, ...                          (脚本写)
            └── lore/<entry-slug>.md ← 每条 character_book entry              (脚本写)
```

空类别会直接跳过不写文件（agent 要么觉得这个桶没东西可放，要么拒绝处理——
两种情况都通过 companion 索引可观察：缺失的文件本身就是信号）。

模型在会话开始时只静态读 SOUL.md 和 companion 文件，之后只在对话需要
某些细节时才打开对应的 `extended/...md`。Hermes 这种是从 cwd 读
`HERMES.md` 的——所以要从 `$HERMES_HOME` 启动 runtime（HERMES.md 必须
能被找到，它是指向各类别文件的索引）。

完整流程（含 `finalize` 步骤和失败模式）见
[`skills/soultavern/references/oversized-cards.md`](skills/soultavern/references/oversized-cards.md)。

## SoulTavern 写哪些文件——以及哪些它绝不写

**会写（只在 `<home>` 内）：** 上面那张图。爆炸半径就这么大。

**绝不写（`--target hermes`）：**

- `AGENTS.md`——按 Hermes 加载器优先级会被 HERMES.md 屏蔽。
- `MEMORY.md`、`USER.md`——归运行中 agent 的 memory 工具管
- `CLAUDE.md`、`.cursorrules`——别的工具的地盘
- 运行时，`<home>` 之外的任何文件
- 任何 runtime 配置 / 渠道白名单 / `platform_toolsets` 条目

**会写（`--target openclaw`）：** SOUL.md（完全替换）、AGENTS.md
（仅 `<!-- BEGIN soultavern:character -->` 标记之间的部分——标记之外
的用户内容原样保留）、IDENTITY.md（完全替换）。

要把一个 `<home>` 完全清干净：
`rm -rf <home>/{SOUL.md,HERMES.md,IDENTITY.md,cards}`，再把
AGENTS.md 里的 soultavern managed section 删掉。其他地方什么都不会泄露。

## 文档

skill 自带文档；`SKILL.md` 和 `references/` 目录是面向操作者的完整说明。

- [`skills/soultavern/SKILL.md`](skills/soultavern/SKILL.md) ——
  导入 + 卡库管理（list / current / switch / delete / restore /
  history / revert）合并在同一份 SKILL.md 里

**参考文档**

- [`v2-spec-summary.md`](skills/soultavern/references/v2-spec-summary.md) — V2 卡字段速查
- [`field-mapping.md`](skills/soultavern/references/field-mapping.md) — V2 → markdown 精确规则
- [`usage-recipes.md`](skills/soultavern/references/usage-recipes.md) — 常见工作流和坑
- [`security.md`](skills/soultavern/references/security.md) — 威胁模型 + 消毒层
- [`oversized-cards.md`](skills/soultavern/references/oversized-cards.md) — 超大卡的 agent 驱动分发流程
- [`library-layout.md`](skills/soultavern/references/library-layout.md) — `<home>/cards/` schema、快照、`--card` 解析

## 仓库布局

```
SoulTavern/
├── tests/                         pytest 套件(含真实卡 smoke)
├── examples/                      本地第三方卡(被 gitignore)
├── pyproject.toml                 dev 工具配置（pytest / ruff / mypy）
└── skills/                        skill 树
    └── soultavern/                单个 skill: 导入 + 卡库管理
        ├── SKILL.md               LLM 入口文档
        ├── scripts/               每个操作的入口脚本 + 引擎 Python 包
        │   ├── import.py  switch.py  list.py  …    LLM 直接调的薄壳
        │   └── soultavern/        Python 包（仅 stdlib）
        │       └── targets/       各 runtime 适配器（hermes / openclaw / generic）
        ├── references/            8 份参考文档
        └── assets/                示例 V2 卡
```

> **v2.0.0 破坏性变更。** `soultavern` CLI 没了。所有操作都变成
> `skills/soultavern/scripts/` 下的脚本。Python 包从 `src/soultavern/`
> 搬到了 `skills/soultavern/scripts/soultavern/`。Wheel 分发、install.sh、
> `hermes-tavern` 向后兼容别名全部移除。完整迁移说明见
> [CHANGELOG.md](CHANGELOG.md#200)。

> **v1.0.0 改名。** v1.0 之前项目叫 **HermesTavern**（单 target，
> 只支持 Hermes-Agent）。v1.0 改名为 **SoulTavern**，加入多 target 支持。

> **v0.5.0 提示。** 更早的版本把卡库管理拆成独立的
> `hermes-tavern-cards` skill，v0.5.0 已经合并进主 skill。

`skills/` 子目录沿用 `openai/skills` 和 `anthropics/skills` 的
`path: "skills/"` 约定，所以支持 tap-style skill 发现的 runtime 不需要
任何额外配置就能跑通。每个 skill 文件夹都用标准的
`references/` / `scripts/` / `assets/` 三件套——只放有内容的子目录。

## 已知限制

- **不做关键词触发的 lorebook 注入。** 所有 entry 都按 always-on 渲染。
  这是用保真度换简洁度，在长上下文模型上工作良好；超大 lorebook 走
  agent 驱动的 extended-files 流程，不走门控。
- **同一个 runtime 实例不支持多角色聊天。** 每个角色用独立的
  `<home>` 跑。
- **没有渠道层安全控制。** 这些请在 runtime 一侧配置（Hermes 的
  `platform_toolsets`、白名单、限速等）。SoulTavern 只写人格文件。
- **不支持热编辑。** runtime 在会话开始时缓存 system prompt，对人格
  文件的修改要等下次会话才生效（Hermes 也可以在会话内用 `/reset`）。

## 已知问题

- **某些 IM 上传 PNG 时会重新编码图片，破坏角色卡数据。**
  SillyTavern V2 卡把真正的角色数据藏在 PNG 的 `tEXt` chunk 里；
  当 IM 重写图片（缩放、剥元数据、转成 JPEG 缩略图等等）时，那个 chunk
  就没了，SoulTavern 也就解不出来。**解决办法：** 上传前把 PNG 打成 zip
  （`zip aldous.zip aldous.png`），让 IM 当二进制 blob 来传，原始字节就
  不会动。runtime 拿到 zip 之后解压再导入就行。
- **审查严的 agent 处理超大卡时可能只完成部分类别分发。**
  当一张卡超过 runtime 的阈值（hermes 是 15k，openclaw 是 9k），
  SoulTavern 把素材摆到磁盘上，由调用方 agent 来分类。如果 agent 受
  策略限制，可能拒绝写某些类别（比如 `kinks.md`），那些类别就会
  缺席最终的 companion 索引——角色还是能加载，只是缺了 agent 不愿
  保留的部分。想拿到更全的版本，换个模型让 agent 重新跑一遍
  `source.md`，再跑 `finalize.py` 即可。

## 开发

```bash
git clone https://github.com/imphillip/SoulTavern.git && cd SoulTavern
python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"      # 仅 pytest / ruff / mypy——没有运行时依赖

pytest                    # 跑全套
pytest -k staging         # 跑子集
pytest tests/test_real_cards_smoke.py   # 真实卡 smoke(没卡时自动 skip)
```

`tests/conftest.py` 会把 `skills/soultavern/scripts/` 加进 `sys.path`，
所以 `from soultavern.parse import load_card` 之类的 import 不需要
`pip install -e .`。运行时包零三方依赖——`[dev]` 只是测试和 lint 工具链。

要拿你自己的卡跑真实 smoke，把它们丢到 `examples/.local/`。
那个目录被 gitignore——社区卡的 license / 体积 / 内容差异太大无法分发，
所以只放在本地。

`tests/` 套件覆盖 parse、render、substitute、sanitize、scan、classify、
staging、extended、finalize、library、CLI、以及端到端 pipeline。
保持绿色。

## 贡献

欢迎 PR。提交前请：

1. 在 `tests/` 下为你的改动加或更新测试。
2. 跑 `pytest` 确认仍然全绿。
3. 如果改了卡 → markdown 的契约，同步更新
   `skills/soultavern/references/field-mapping.md` 让规范和代码对齐。
4. 给某个 `scripts/*.py` 入口加新 flag 时，记得在相关 `SKILL.md` 和
   README 的"常用命令"段提一句。

设计讨论、bug 报告、功能请求，issue 也欢迎。

## 被使用情况

[agentbox.id](https://agentbox.id) 的 `soul-loader` —— Hermes 与 OpenClaw
runtime 下 agentbox 官方的灵魂加载入口 —— 把 SoulTavern 作为底层
引擎调用。详见
[`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md)。

## 协议

[MIT](LICENSE) — © 2026 SoulTavern contributors。
