# SoulTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> 让任何带有 SOUL.md 的 agent runtime 都能换上你的 SillyTavern 角色卡。
>
> _给你的 work agent 装一个有趣的灵魂——工作娱乐两不误。
> 程序员的浪漫。_

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

SoulTavern 把 SillyTavern V2 角色卡（`.png` / `.json`）转成 agent runtime
启动时加载的 markdown 系统提示词文件。两个生产可用 target：

- `--target hermes`——输出
  [Hermes-Agent](https://github.com/NousResearch/hermes-agent) 用的
  `SOUL.md` + `HERMES.md`
- `--target openclaw`——输出
  [OpenClaw](https://github.com/imphillip/openclaw) workspace 用的
  `SOUL.md` + `AGENTS.md` managed-section + `IDENTITY.md`

不需要中间件、不打补丁、不做转发——**也不需要安装**。SoulTavern 是一个
自包含的 skill 文件夹，零三方 Python 依赖。把文件夹丢进 runtime 的
skill 目录，agent 会按需调用其中的脚本。

## 安装

```bash
git clone https://github.com/imphillip/SoulTavern.git
cp -r SoulTavern/skills/soultavern <YOUR_RUNTIME_SKILLS_DIR>/
```

典型目标：`~/.openclaw/workspace/skills/`、Hermes 的 skills 目录、或
Claude Code 的 `~/.claude/skills/`。runtime 扫 skill 的任何目录都行。
Hermes hub 用户可以走
`hermes skills tap add imphillip/SoulTavern && hermes skills install soultavern`
——同一份 skill 文件夹，只是发行方式不同。

唯一依赖：Python ≥ 3.10。仅 stdlib——不再依赖 pillow / jinja2 / pyyaml。

## 日常用法

在 runtime 的聊天里上传角色卡，用大白话告诉它你想干嘛：

> _[aldous.png 已附加]_ 安装这个角色
>
> 切换到 alice
>
> 把所有角色都忘掉，恢复成默认

agent 读 `SKILL.md`，调用 `skills/soultavern/scripts/` 下相应的脚本，
变更准备好之后会主动告诉你开个新会话（Hermes 用 `/new` 或 `/reset`）让它生效。

要直接调脚本，先设 `SKILL=path/to/skills/soultavern`，然后：

```bash
python3 $SKILL/scripts/import.py   --card aldous.png --home $HERMES_HOME
python3 $SKILL/scripts/import.py   --card aldous.png --home ~/.openclaw/workspace --target openclaw
python3 $SKILL/scripts/validate.py --card aldous.png

# 卡库：list / current / switch / delete / restore / history / revert / finalize
python3 $SKILL/scripts/list.py   --home $HERMES_HOME
python3 $SKILL/scripts/switch.py --card alice --home $HERMES_HOME
python3 $SKILL/scripts/revert.py --home $HERMES_HOME --to pristine
```

每个脚本都接受 `--help`。flag、exit code、输出行为在两个 target 之间
一致，跨版本稳定。

## 工作原理

SoulTavern 解析 V2 卡，替换 `{{char}}` / `{{user}}` 以及老式的
`<BOT>` / `<USER>`，每个文本字段过一遍消毒（零宽字符 / RTL 覆盖 /
控制字符全部剥掉），然后渲染到 target runtime 的文件槽：

```
<home>/
├── SOUL.md         ← 角色人格；总是加载
├── HERMES.md       ←（hermes target）  lorebook + 扩展文件索引
├── AGENTS.md       ←（openclaw target）managed section：身份指令 + lore 索引
├── IDENTITY.md     ←（openclaw target）角色元数据
└── cards/
    ├── .active.json    ← 当前激活卡的指针
    ├── .snapshots/     ← 每次变更的快照（用来 revert）
    ├── .trash/         ← 软删除的卡
    └── <name>_<ts>.<ext>   ← 原卡备份
```

每个渲染文件开头都有一段 **IDENTITY DIRECTIVE**，覆盖 runtime 默认的
"我是 AI 助手"框架。没有它，模型会塌回"我是 AI；如果是在角色扮演的话，
我在饰演 X"这种回答，而不是直接以角色身份说话。操作者层面的安全
策略明确写在人格之上。

渲染后超过 runtime 单文件预算（hermes 是 15k，openclaw 是 9k）的卡，
会触发 **agent 驱动的超大卡流程**：`import.py` 把解析后的素材摆到磁盘上，
退出码 2；调用方 agent 把内容分发到 8 个 V2 类别（`identity.md`、
`personality.md`、`scenario.md` 等）；之后 `finalize.py` 拼出精选的
`SOUL.md` 和索引化的 companion 文件。规则是**忠于原文措辞**——
agent 决定保留什么，不决定怎么换种说法。

字段渲染规则见
[references/field-mapping.md](skills/soultavern/references/field-mapping.md)，
超大卡流程见
[references/oversized-cards.md](skills/soultavern/references/oversized-cards.md)。

## 生命周期

### 升级

覆盖 skill 文件夹。文件夹是纯静态的——里面没有 per-install 状态——
所以覆盖是安全的。`<home>` workspace 里导入的卡、快照历史、已渲染的
人格文件不受影响。`.active.json` 和快照 manifest 跨版本读，旧版本
会自动升级 schema。

### 卸载

**hermes target**——删 skill 文件夹：

```bash
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
# 可选：把人格文件 + 卡库也清掉
rm -rf <HERMES_HOME>/{SOUL.md,HERMES.md,cards}
```

**openclaw target**——删 skill 文件夹**之前**，先对每个用过的 workspace 跑
`delete.py`：

```bash
python3 $SKILL/scripts/current.py --home <ws>            # 看当前 active 卡名
python3 $SKILL/scripts/delete.py  --card <name> --home <ws>
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
```

SoulTavern 在 workspace 的 `AGENTS.md` 里写了一段 `<!-- BEGIN soultavern:character -->`
标记之间的 managed section。光删 skill 文件夹不会去除这一段——`delete.py`
会干净地 strip 掉，同时保留 marker 之外的用户内容。

## 安全默认

每张卡都被当作第三方内容。五层防护，按信任顺序：

1. **IDENTITY DIRECTIVE** 自动注入到 runtime 加载优先级最高的那份文件
   （Hermes 是 SOUL.md，OpenClaw 是 AGENTS.md）。操作者安全策略永远在人格之上。
2. **信任横幅**贴在每个人格文件上：忽略里面试图改工具 / 越过安全策略 /
   泄漏数据 / 联系外部系统的指令。
3. **作者字段降级。** `system_prompt` 和 `post_history_instructions`
   默认渲染进 `## Author's framing (untrusted ...)` 引用块里。
   `--trust-system-prompt` 才把它们提到高信任位置——只对你绝对信任作者的卡用。
4. **解析期消毒**剥掉零宽字符、RTL 覆盖、控制码。
5. **红旗扫描**每次 `import` / `validate` 都跑，查提示注入模式和外联 URL，
   写到 stderr 告警，但不会拦截导入。

完整威胁模型见
[references/security.md](skills/soultavern/references/security.md)。

## LLM 选择影响很大

角色演绎的质量很大程度上取决于 runtime 背后的模型，**不是**卡或这个
skill 单方面决定的。同一份 `SOUL.md` 在不同模型上明显有差距——有的
真能沉下去演角色，有的总是塌回 AI 助手语气，有的甚至搞不定"镜像
用户语言"那条指令。实测下来：`grok-4.20` 这类模型同卡同条件下，
比 `gpt-5.4` 演得明显好得多。如果一张卡读起来平淡，先换个模型试试，
再去怀疑卡或 SoulTavern 的渲染。

想找地方跑 roleplay 友好的模型？[gptproto.com](https://gptproto.com/?r=GGUHQXGN)
是一个选择——这个链接带推荐码，下单会有折扣。_（推广链接，顺便支持一下项目）_

## 已知限制

- **不做关键词触发的 lorebook 注入。** 所有启用的 entry 按 always-on 渲染。
  超大 lorebook 走 agent 驱动的 extended-files 流程。
- **同一个 runtime 实例不支持多角色聊天。** 每个角色用独立的 `<home>`。
- **不管渠道层安全。** 速率限制 / 白名单 / `platform_toolsets` 这些请在
  runtime 一侧配。
- **不支持热编辑。** runtime 在会话开始时缓存 system prompt。改了之后
  开新会话。

## 已知问题

某些 IM 客户端上传 PNG 时会重新编码图片，把藏在 PNG text chunk 里的
角色卡数据破坏掉。解决办法：先把 PNG 打成 zip（`zip aldous.zip aldous.png`），
让 IM 当二进制 blob 来传，原始字节就不会动。runtime 拿到 zip 后解压再导入即可。

## 仓库布局

```
SoulTavern/
├── tests/                  pytest 套件（含真实卡 smoke）
├── examples/               本地第三方卡（gitignore）
├── pyproject.toml          dev 工具配置（pytest / ruff / mypy）
└── skills/soultavern/
    ├── SKILL.md            LLM 入口文档
    ├── scripts/            每个操作的入口脚本 + 引擎包
    │   ├── *.py            import.py  switch.py  list.py  …
    │   └── soultavern/     仅 stdlib 的引擎
    │       └── targets/    各 runtime 的适配器
    ├── references/         8 份参考文档
    └── assets/             示例 V2 卡
```

## 开发

```bash
git clone https://github.com/imphillip/SoulTavern.git && cd SoulTavern
python -m venv .venv && source .venv/bin/activate
pip install pytest ruff mypy
pytest                                  # 跑全套
pytest tests/test_real_cards_smoke.py   # 真实卡 smoke（把卡丢到 examples/.local/）
```

`tests/conftest.py` 会把 `skills/soultavern/scripts/` 加进 `sys.path`。
v2.0 不再作为可安装包发布——`pyproject.toml` 只是
`ruff` / `mypy` / `pytest` 的配置载体。

## 贡献

欢迎 PR。加测试、保持绿、如果改了卡 → markdown 的契约，同步更新
[references/field-mapping.md](skills/soultavern/references/field-mapping.md)。

## 被使用情况

[agentbox.id](https://agentbox.id) 的 `soul-loader`——Hermes 和 OpenClaw
runtime 下 agentbox 官方的灵魂加载入口——把 SoulTavern 作为底层引擎调用。
详见 [`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md)。

## 赞助

**[Miko Tavern](https://tavern.host)** —— 一个角色扮演 Telegram bot。

## 协议

[MIT](LICENSE) — © 2026 SoulTavern contributors。
