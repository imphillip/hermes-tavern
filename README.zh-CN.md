# HermesTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> 在 Hermes 智能体里跑你的 SillyTavern 角色卡。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

HermesTavern 是一个一次性导入工具，把 SillyTavern V2 角色卡
(`.png` / `.json` / `.yaml`) 转成 [Hermes-Agent](https://github.com/NousResearch/hermes-agent)
启动时加载的两份 markdown 文件——分别承担身份 (`SOUL.md`) 和项目上下文
(`HERMES.md`) 两个槽位。

不需要中间件、不打补丁、不做转发。把卡丢进去、拿出 markdown、指给 Hermes，
你的 agent 就进入角色——而且 Hermes 已经接通的所有渠道都同步生效
（CLI、邮件、Telegram、Discord、Slack……）。

**血缘:** `TavernAI` → `SillyTavern` → **`HermesTavern`**

---

## 怎么用

Hermes 本身就是一个相当成熟的 AI agent——理解意图、下载附件、调用合适的工具
样样都行。HermesTavern 装好之后，所有用户面交互都是自然语言对话，没有任何
指令需要记。

在你的 Hermes 聊天里（Telegram、Discord、QQ、邮件——任何 Hermes 已经能
说话的渠道），上传角色卡文件，然后用大白话告诉它你想干嘛：

> _[aldous.png 已附加]_ 安装这个角色

> 切换到 alice

> 把所有角色都忘掉，恢复成默认 Hermes

就这些。Hermes 解析你的意图，在背后调用 `hermes-tavern`，
变更准备好之后会主动告诉你执行 `/new` 或 `/reset` 让它生效。
有歧义的时候直接用大白话再说一句——剩下交给 Hermes。

## 安装

一次文件上传。Hermes 跑起来之后就完全不用碰终端：

```bash
git clone https://github.com/imphillip/hermes-tavern.git
cd hermes-tavern && zip -r hermes-tavern-skills.zip skills/
```

在 Hermes 聊天里把 `hermes-tavern-skills.zip` 上传过去，然后说
**"装一下这个 skill"**。打包整个 `skills/` 目录，不要单独打某个子 skill——
Hermes 期望看到 `skills/<name>/SKILL.md` 这种布局，并且会用
`skills/hermes-tavern/assets/` 里捆绑的 wheel 把 `hermes-tavern` CLI 装进 PATH。

之后所有交互就是上面演示的那种"上传 + 说话"模式。

### 或者通过 Hermes hub

如果你的 Hermes 已经配好了 hub `tap` 系统：

```bash
hermes skills tap add imphillip/hermes-tavern
hermes skills install hermes-tavern hermes-tavern-cards
```

### Bootstrap：在主机上直接装 CLI

只在 Hermes 自己还跑不起来、没法替你装的时候才需要（比如初始化一台新的 Hermes
主机，或者要在另一台机器上单独装 CLI）：

```bash
git clone https://github.com/imphillip/hermes-tavern.git && cd hermes-tavern
bash skills/hermes-tavern/scripts/install.sh
```

幂等——依次尝试 `pipx` → `uv tool` → 在 `~/.local/share/hermes-tavern-venv`
里建一个专用 venv，并往 `~/.local/bin` 放 shim。可用 `HERMES_TAVERN_VENV` /
`HERMES_TAVERN_BIN` 覆盖路径。等 `hermes-tavern` 上 PyPI 之后，
这一段会简化为 `pipx install hermes-tavern`，捆绑的 wheel 也就可以删掉了。

### 依赖

- Python ≥ 3.10
- 想给超大角色卡用蒸馏功能的话，需要一个能跑的
  [`hermes`](https://github.com/NousResearch/hermes-agent) CLI
  （默认 `--distill-cmd "hermes -q"`；可用 `--distill-cmd` 覆盖，
  或用 `--no-distill` 跳过）

---

## 缘起

Hermes 启动时本来就会把 `SOUL.md`（独立身份槽）和 `HERMES.md`（cwd 相关的
项目上下文槽）自动加载进 system prompt。唯一缺的是一个尊重 SillyTavern V2
schema、占位符语法（`{{char}}`、`{{user}}`、`<BOT>`、`<USER>`）以及
lorebook 布局的转换器。HermesTavern 就是来补这一环的。

刻意不做的事：

- 改 Hermes 源码
- 写中间件 / 转发层
- 碰渠道配置（`platform_toolsets`、白名单……）
- 启动或托管 Hermes 进程
- 写 `AGENTS.md`、`MEMORY.md`、`USER.md`、`CLAUDE.md`

## 功能

- **V2 + V1 + PNG + YAML 解析**——SillyTavern 在野的所有容器形态全收
- **占位符替换**——`{{char}}` / `{{user}}` 加上老式的 `<BOT>` / `<USER>`，
  大小写不敏感、不递归
- **Lorebook → HERMES.md 渲染**——按 `insertion_order` 排序，
  禁用条目跳过，超长尾部截断
- **身份指令**——每份 SOUL.md 顶部自动注入，覆盖 hermes 内置的"你是 AI
  助手"框架，让模型直接以角色身份回答，避免出现"我是 AI；如果是在角色扮演
  的话，我在饰演 X"这种回答
- **三层安全**——可见的信任横幅、解析期消毒（零宽字符 / RTL 覆盖 /
  控制字符清理）、按提示注入类别做的红旗模式扫描
- **蒸馏管道**——当卡片渲染后超过 Hermes 20k 槽 75% 的阈值，
  shell out 调 `hermes -q` 压缩进 prompt 的部分，
  原始内容则按字段平铺到磁盘，供运行时按需读取
- **角色卡库**——对已导入到 `HERMES_HOME` 的卡做 list / current / switch /
  delete / restore
- **快照历史**——每次 `import` / `switch` / `revert` 都被捕获到
  `cards/.snapshots/`，还有一个特殊的 `pristine` 快照保存装卡前的原状。
  `revert --to pristine` / `--previous` / `--to <id|name>` 可以回溯历史
- **渠道无关**——产生的是 Hermes 启动时加载的人格文件；
  Hermes 能说话的所有地方都自动在角色里

## 常用命令

```bash
# 检查一张卡（解析 + 渲染 + 扫描，不写文件）
hermes-tavern validate --card aldous.png

# 预览渲染好的 markdown
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --dry-run

# 替换已存在的人格
hermes-tavern import --card alice.png --home ~/.hermes-roleplay --overwrite

# 卡库管理
hermes-tavern list    --home ~/.hermes-roleplay [--all]
hermes-tavern current --home ~/.hermes-roleplay
hermes-tavern switch  --card alice --home ~/.hermes-roleplay
hermes-tavern delete  --card bob   --home ~/.hermes-roleplay
hermes-tavern restore --card bob   --home ~/.hermes-roleplay

# SOUL.md / HERMES.md 快照历史（每次 import/switch 都会捕获）
hermes-tavern history --home ~/.hermes-roleplay
hermes-tavern revert  --home ~/.hermes-roleplay --to pristine     # 回到装卡前的状态
hermes-tavern revert  --home ~/.hermes-roleplay --previous        # 回退一格
hermes-tavern revert  --home ~/.hermes-roleplay --to 0003

# 信任卡作者的 system_prompt / post_history_instructions
# （默认会渲染进不可信引用块里）
hermes-tavern import ... --trust-system-prompt

# 关掉超大卡的蒸馏（让原始的预算超限错误浮出）
hermes-tavern import ... --no-distill

# 用别的命令做蒸馏
hermes-tavern import ... --distill-cmd "claude -p"
```

`switch` / `delete` / `restore` 接受文件名或角色名（对解析得到的 `name`
字段或文件名 stem 做大小写不敏感的前缀匹配）。

## 运行模式

HermesTavern 按渲染后的体积自动选择两种模式之一。阈值是 Hermes 20k 槽的
75%——也就是 15,000 字符——SOUL.md 或 HERMES.md **任意一个**超过都会触发。

### 普通模式（每个槽渲染输出 ≤ 15k）

```
<HERMES_HOME>/
├── SOUL.md                          ← 渲染后的人格
├── HERMES.md                        ← 渲染后的 lorebook
│                                       (仅当卡有 character_book 时)
└── cards/
    ├── .active.json                 ← 当前激活卡的指针
    ├── .snapshots/<NNNN>_…/         ← SOUL.md / HERMES.md 历史
    ├── .trash/                      ← 软删除的卡 (delete/restore)
    └── <name>_<ts>.<ext>            ← 原卡备份
```

### 蒸馏模式（SOUL 或 HERMES 渲染后 > 15k）

HermesTavern 会 shell out 调你已配好的 Hermes CLI（默认 `hermes -q`），
对渲染输出做一次性 LLM 压缩，然后把**完整的原始内容**按字段平铺到磁盘，
让模型在运行时按需读取。

```
<HERMES_HOME>/
├── SOUL.md                          ← LLM 蒸馏后的人格(精简)
├── HERMES.md                        ← 蒸馏后的 lore + 扩展文件索引
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← 原卡备份
    └── <name>_<ts>/
        └── extended/                ← 完整原始内容,按字段
            ├── description.md
            ├── personality.md
            ├── scenario.md
            ├── first_mes.md
            ├── mes_example.md
            ├── system_prompt.md
            ├── post_history_instructions.md
            ├── alternate_greetings/01.md, 02.md, ...
            └── lore/<entry-slug>.md
```

模型在会话开始时只静态读 SOUL.md 和 HERMES.md，之后只在对话需要某些细节时
才打开对应的 `extended/...md`——所以蒸馏模式下 `cd $HERMES_HOME` 更加重要
（HERMES.md 是指向各字段文件的索引）。

用 `--no-distill` 关掉蒸馏（让原始的预算超限错误浮出）。
用 `--distill-cmd "<command>"` 覆盖蒸馏命令。完整管道见
[`skills/hermes-tavern/references/distillation.md`](skills/hermes-tavern/references/distillation.md)。

## HermesTavern 写哪些文件——以及哪些它绝不写

**会写（只在 `<HERMES_HOME>` 内）：** 上面那张图。爆炸半径就这么大。

**绝不写：**

- `AGENTS.md`——按 Hermes 加载器优先级会被 HERMES.md 屏蔽
- `MEMORY.md`、`USER.md`——归运行中 agent 的 memory 工具管
- `CLAUDE.md`、`.cursorrules`——别的工具的地盘
- 运行时，`<HERMES_HOME>` 之外的任何文件
- 任何 Hermes 配置 / 渠道白名单 / `platform_toolsets` 条目

要把一个 `HERMES_HOME` 完全清干净：
`rm -rf <home>/{SOUL.md,HERMES.md,cards}`——其他地方什么都不会泄露。

## 文档

两个 skill 自带文档；它们的 `SKILL.md` 和 `references/` 目录是面向操作者
的完整说明。

**Skills**

- [`skills/hermes-tavern/SKILL.md`](skills/hermes-tavern/SKILL.md) ——
  导入 & 校验
- [`skills/hermes-tavern-cards/SKILL.md`](skills/hermes-tavern-cards/SKILL.md) ——
  list / current / switch / delete / restore

**参考文档（loader skill）**

- [`v2-spec-summary.md`](skills/hermes-tavern/references/v2-spec-summary.md) — V2 卡字段速查
- [`field-mapping.md`](skills/hermes-tavern/references/field-mapping.md) — V2 → markdown 精确规则
- [`usage-recipes.md`](skills/hermes-tavern/references/usage-recipes.md) — 常见工作流和坑
- [`security.md`](skills/hermes-tavern/references/security.md) — 威胁模型 + 消毒层
- [`distillation.md`](skills/hermes-tavern/references/distillation.md) — 超大卡管道

**参考文档（cards skill）**

- [`library-layout.md`](skills/hermes-tavern-cards/references/library-layout.md) — `<HERMES_HOME>/cards/` schema、`--card` 解析

## 仓库布局

```
hermes-tavern/
├── src/hermes_tavern/             Python 包(引擎; PyPI 之前是捆绑 wheel)
├── tests/                         pytest 套件(含真实卡 smoke)
├── examples/                      本地第三方卡(被 gitignore)
└── skills/                        Hermes hub 可发现的 skill 树
    ├── hermes-tavern/             Skill 1: 导入 & 校验
    │   ├── SKILL.md
    │   ├── references/            5 份参考文档
    │   ├── scripts/               skill 入口 wrapper + install.sh
    │   └── assets/                捆绑 wheel + 示例 V2 卡
    └── hermes-tavern-cards/       Skill 2: 卡库管理(依赖 hermes-tavern)
        ├── SKILL.md
        ├── references/            library-layout 文档
        └── scripts/               skill 入口 wrapper
```

`skills/` 子目录沿用 `openai/skills` 和 `anthropics/skills` 的
`path: "skills/"` 约定，所以 `hermes skills tap add imphillip/hermes-tavern`
不需要任何额外配置就能跑通。每个 skill 文件夹都用标准的
`references/` / `scripts/` / `assets/` 三件套——只放有内容的子目录。

## 已知限制

- **不做关键词触发的 lorebook 注入。** 所有 entry 都按 always-on 渲染。
  这是用保真度换简洁度，在长上下文模型上工作良好；超大 lorebook 走蒸馏，
  不走门控。
- **同一个 Hermes 实例不支持多角色聊天。** 每个角色用独立的
  `HERMES_HOME` 跑。
- **没有渠道层安全控制。** 这些请在 Hermes 一侧配置（`platform_toolsets`、
  白名单、限速）。HermesTavern 只写人格文件。
- **不支持热编辑。** Hermes 在会话开始时缓存 system prompt，对 `SOUL.md` /
  `HERMES.md` 的修改要等下次会话或在 hermes 里 `/reset` 之后才生效。

## 已知问题

- **某些 IM 上传 PNG 时会重新编码图片，破坏角色卡数据。**
  SillyTavern V2 卡把真正的角色数据藏在 PNG 的 `tEXt` chunk 里；
  当 IM 重写图片（缩放、剥元数据、转成 JPEG 缩略图等等）时，那个 chunk
  就没了，HermesTavern 也就解不出来。**解决办法：** 上传前把 PNG 打成 zip
  （`zip aldous.zip aldous.png`），让 IM 当二进制 blob 来传，原始字节就
  不会动。Hermes 拿到 zip 之后解压再导入就行。
- **超大卡的蒸馏在内容审查严的模型上可能卡很久。**
  当一张卡超过 15k 阈值，HermesTavern 会 shell out 到 `hermes -q` 做 LLM
  压缩。如果卡里有成人内容或其他踩内容政策的素材，而底下的 LLM 审查严，
  这次调用就可能明显变慢（重试、流式吐字慢、硬拒绝），慢到让人以为卡死了。
  HermesTavern 这边没有干净的修法：给这类卡换一个限制宽松点的模型。
  懂的都懂。

## 开发

```bash
git clone https://github.com/imphillip/hermes-tavern.git && cd hermes-tavern
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                    # 跑全套
pytest -k distill         # 跑子集
pytest tests/test_real_cards_smoke.py   # 真实卡 smoke(没卡时自动 skip)
```

要拿你自己的卡跑真实 smoke，把它们丢到 `examples/.local/`。
那个目录被 gitignore——社区卡的 license / 体积 / 内容差异太大无法分发，
所以只放在本地。

`tests/` 套件覆盖 parse、render、substitute、sanitize、scan、extended、
distill（mock LLM）、library、CLI、以及端到端 pipeline。保持绿色；
非 mock 的 subprocess 测试用临时目录里写出来的小 fake `hermes` shell 脚本。

## 贡献

欢迎 PR。提交前请：

1. 在 `tests/` 下为你的改动加或更新测试。
2. 跑 `pytest` 确认仍然全绿。
3. 如果改了卡 → markdown 的契约，同步更新
   `skills/hermes-tavern/references/field-mapping.md` 让规范和代码对齐。
4. 加新 CLI flag 时，记得在相关 `SKILL.md` 和 README 的"常用命令"段提一句。

设计讨论、bug 报告、功能请求，issue 也欢迎。

## 被使用情况

[agentbox.id](https://agentbox.id) 的 `soul-loader` —— agentbox 的灵魂加载入口 ——
在 Hermes 运行时下安装并调用 HermesTavern。
详见 [`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md)。

## 协议

[MIT](LICENSE) — © 2026 HermesTavern contributors。
