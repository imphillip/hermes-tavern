# SoulTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> SOUL.md を読み込むあらゆる agent runtime で SillyTavern キャラクターを動かす。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

SoulTavern は SillyTavern V2 キャラクターカード(`.png` / `.json`)を、
agent runtime が起動時に読み込むマークダウンシステムプロンプトファイル
へ変換するワンショットインポーターです。v2.0 は 2 つの target を提供:
`--target hermes` ([Hermes-Agent](https://github.com/NousResearch/hermes-agent)
用の `SOUL.md` + `HERMES.md` を出力)と `--target openclaw`
([OpenClaw](https://github.com/imphillip/openclaw) workspace 用の
`SOUL.md` + `AGENTS.md` managed-section + `IDENTITY.md` を出力)。

ミドルウェアもパッチもリレーも、**インストールも不要**。SoulTavern は
完全自己完結の skill フォルダで、Python サードパーティ依存はゼロ。
runtime が skill を読みに行くディレクトリへフォルダを置き、スクリプトを
直接呼ぶ——以上。

**系譜:** `TavernAI` → `SillyTavern` → `HermesTavern` → **`SoulTavern`**

> SoulTavern v2.0 は skill-folder-only 配布へ収束しました。`soultavern`
> CLI(と `hermes-tavern` 後方互換エイリアス)は廃止され、すべての操作は
> `skills/soultavern/scripts/` 配下のスクリプトです。`--target hermes` /
> `--target openclaw` の出力は v1.0 とバイト単位で同一——変わったのは
> 呼び出し方だけ。移行手順は [CHANGELOG.md](CHANGELOG.md#200) 参照。

---

## ビジョン: HermesTavern から SoulTavern へ

HermesTavern は、より大きな方向性の最初の具体例です——「セッション
開始時に永続的な人格ファイルを読み込む」あらゆる agent runtime に、
SillyTavern キャラクターカードのエコシステム全体を接続可能にする、
というのが大きな方向性です。

**SoulTavern** はこの方向性を多 target で抽象化したものです。今日の
プロダクション target は 2 つ: `--target hermes` (デフォルト;
`SOUL.md` + `HERMES.md` を出力) と `--target openclaw`
(`SOUL.md` + `AGENTS.md` managed-section + `IDENTITY.md` を出力)。
汎用 `--target generic` フォールバックはスケルトンとして登録済み
で、後続リリースで完成します。

### 3 つの原則

1. **「魂の可搬性」を優先し、「機能の完璧再現」は追わない。**
   SillyTavern や RisuAI は重度 RP のための場であり、SoulTavern が
   扱うのは一方向ポーティング——コミュニティが作成済みの何千もの
   V2 キャラクターカードを、SillyTavern のプロトコルをネイティブに
   話さない agent runtime へ搬入する作業です。失う 30-40%
   (トークンストリーミング、swipe/regen/branch、キーワードトリガ
   lorebook 挿入)は channel/UI 層のメカニズムで、意図的に追求し
   ません。移植できる 70-80% で軽度〜中度 RP のほとんどはカバー
   できます。

2. **ファイル単位の適応が普遍的なインターフェース。** セッション
   開始時に markdown システムプロンプトファイルを読み込む agent
   runtime はすべて適応対象になります。適応は 2 層: (a) V2
   フィールドをその runtime 固有のファイル群へレンダリング(Hermes は
   `SOUL.md` + `HERMES.md`;OpenClaw は `SOUL.md` + `IDENTITY.md` +
   `AGENTS.md`)、(b) その runtime のローダー優先度が最も高い
   ファイル(Hermes なら SOUL.md、OpenClaw なら AGENTS.md)に
   **IDENTITY DIRECTIVE** を注入し、デフォルトの「私は AI アシスタント
   です」フレーミングを抑え込む。(b) が要——抑えられないと、agent は
   魂の衣を被っただけの自分自身のままです。

3. **ツールは決定的処理、LLM 仕事は agent に。** Python スクリプトは
   独立した LLM へ shell out しません(v0.4.0 で踏んだ轍、v0.4.5 で
   修正済み)。カードが常時コンテキストの容量を超えた場合、`import.py`
   は `source.md` をディスクに置き、終了コード 2 で抜けます; 呼び出し
   側の agent が自身のコンテキストで自身のファイルツールを用いて
   V2 分類を実行します。これによりツールは LLM CLI のバージョン
   進化に依存せず、agent は第三者ファイルを扱う際の信頼姿勢を
   そのまま適用できます——ポリシーと衝突する内容は正々堂々と
   拒否でき、欠落はインデックスで可視化される(これは誠実なシグナル
   であり、密かな書き換えではありません)。

---

## 使い方

runtime が SoulTavern skill フォルダの場所を知ってさえいれば、ユーザー側の
UX は完全に会話ベースです。runtime のチャットでカードファイルを
アップロードし、自然な日本語で伝えるだけ:

> _[aldous.png 添付]_ このキャラクターをインストールして

> alice に切り替えて

> すべてのキャラを忘れて、デフォルトに戻して

それで全部です。runtime は意図を解釈し、裏で対応する SoulTavern スクリプトを
呼び出し、変更を反映するために新しいセッション(Hermes なら `/new` または
`/reset`)を始めるよう促します。曖昧な点があれば普段の言葉で言い直すだけ。

## インストール

**インストール手順はありません。** SoulTavern は skill フォルダで、
ランタイム依存は Python ≥ 3.10 のみ。runtime が skill を読みに行く
ディレクトリにフォルダを置けば終わりです。

```bash
git clone https://github.com/imphillip/SoulTavern.git
cp -r SoulTavern/skills/soultavern <YOUR_RUNTIME_SKILLS_DIR>/
```

これだけ。runtime 側の agent が `skills/soultavern/SKILL.md` を読み、
必要に応じて `python3 .../scripts/import.py` 等を呼び出します。
PATH 操作なし、wheel ビルドなし、`pipx` なし、グローバル状態なし。

`<YOUR_RUNTIME_SKILLS_DIR>` は runtime によって違います: 典型例は
`~/.openclaw/workspace/skills/`、Hermes の skills ディレクトリ、
Claude Code なら `~/.claude/skills/`。runtime が skill をスキャンする
ディレクトリならどこでも動きます。

### あるいは runtime の skill hub 経由

runtime が hub-style "tap" をサポートしていれば(Hermes など):

```bash
hermes skills tap add imphillip/SoulTavern
hermes skills install soultavern
```

hub インストーラも同じ skill フォルダを置くだけで、それ以外は何もしません。

### アップグレード

skill フォルダを新しいバージョンで上書きします:

```bash
git pull   # SoulTavern の checkout 内で
cp -r SoulTavern/skills/soultavern <YOUR_RUNTIME_SKILLS_DIR>/
```

(hub 経由なら `hermes skills install soultavern` を再実行するだけ。)

skill フォルダは完全に静的です——内部にインストールごとの状態は何も
ないため、上書きしても安全です。インポート済みのカード、スナップ
ショット履歴、レンダリング済みのペルソナファイルは `<home>` workspace
に置かれていて、アップグレードを跨いでも変化しません。`.active.json`
の schema は v1.0 以降安定しているため、古いバージョンが書いた
workspace に対するマイグレーションは必要ありません。

### アンインストール

クリーンに片付ける手順は、どの target を使ったかで分かれます。

**hermes target だけ使った場合:** skill フォルダを削除するだけ:

```bash
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
```

必要なら、使ったそれぞれの `HERMES_HOME` のレンダリング済みペルソナ
ファイルとカードライブラリも除去:

```bash
rm -rf <HERMES_HOME>/{SOUL.md,HERMES.md,cards}
```

`SOUL.md` / `HERMES.md` / `cards/` は SoulTavern が書いたものですが
**ユーザーコンテンツ扱い**(ペルソナ + スナップショット + カード
バックアップ)なので、保持するか消すかはユーザーに任されます。

**openclaw target を使った場合:** skill フォルダを削除する **前に**、
それぞれの workspace に対して `delete.py` を走らせてください:

```bash
# SoulTavern を使った各 openclaw workspace に対して:
python3 <SKILL_DIR>/scripts/current.py --home <ws>          # 現在 active なカード名を確認
python3 <SKILL_DIR>/scripts/delete.py  --card <name> --home <ws>

# その後で skill フォルダを削除:
rm -rf <YOUR_RUNTIME_SKILLS_DIR>/soultavern
```

理由: SoulTavern は workspace の `AGENTS.md` に managed section
(`<!-- BEGIN soultavern:character -->` から対応する `END` マーカーまで)
を書き込みます。skill フォルダを削除しただけではこの section は
strip されません——`AGENTS.md` に静的なマークダウンとして残り続け、
新しいセッションのたびに runtime はそのキャラクターの
IDENTITY DIRECTIVE を読み込み続けます。active カードに対して
`delete.py` を走らせると、managed section をきれいに strip し、
`IDENTITY.md` と `SOUL.md` を削除し、`AGENTS.md` のマーカー外の
ユーザー記述は保持します。

`delete.py` を走らせたくない場合は、各 `AGENTS.md` を手で開いて
`<!-- BEGIN soultavern:character -->` から
`<!-- END soultavern:character -->` までの内容(マーカー本体を含む)を
削除してください。

`<ws>/cards/` のカードライブラリ(バックアップ + スナップショット)は
managed section とは独立しているので、保持/削除を別々に決められます。

### 必要環境

- Python ≥ 3.10(stdlib のみ——pillow / jinja2 / pyyaml への依存はもうない)。
- 大きなカードの処理は、呼び出し側の agent(Hermes 自身、もしくは
  インポートを駆動している任意の agent)が担当します。スクリプトが
  `source.md` をディスクに置き、agent が自分のファイルツールで
  カテゴリ別ファイルへ書き分けます。独立した LLM CLI を shell out
  することはありません。

---

## なぜ作ったか

Hermes は起動時に `SOUL.md`(独立したアイデンティティスロット)と
`HERMES.md`(cwd 相対のプロジェクトコンテキストスロット)を system prompt に
自動読み込みします。唯一足りなかったのは、SillyTavern V2 schema、プレース
ホルダー文法(`{{char}}`、`{{user}}`、`<BOT>`、`<USER>`)、ロアブック
レイアウトを尊重するコンバーターです。それが SoulTavern の `--target hermes`
の役割です。

OpenClaw も同じ構造を持ちます——`SOUL.md` + `AGENTS.md` + `IDENTITY.md` が
セッション開始時の bootstrap 予算で読み込まれます——ただしローダー優先度
の順序が逆で(AGENTS.md が SOUL.md より上位なので、IDENTITY DIRECTIVE は
AGENTS.md に置く必要がある)。これが `--target openclaw` です。

意図的にやらないこと:

- runtime へのパッチ
- ミドルウェア / リレーの作成
- チャンネル設定の改変(`platform_toolsets`、許可リスト、…)
- runtime プロセスの起動・監視
- `MEMORY.md` / `USER.md` / `CLAUDE.md` への書き込み
- `AGENTS.md` のうち openclaw managed-section マーカー外への書き込み
  (`--target hermes` は `AGENTS.md` に一切触れない;`--target openclaw`
  は marker 間のみを書き換え、marker 外のユーザー記述は保持)

## 機能

- **V2 + V1 + PNG 解析** —— 野生の SillyTavern が出す JSON / PNG
  コンテナ形式全般に対応(v2.0 で YAML サポートを廃止;エコシステム
  での利用は無視できるレベル)
- **プレースホルダー置換** —— `{{char}}` / `{{user}}` に加えてレガシーの
  `<BOT>` / `<USER>`、大文字小文字を区別せず、再帰なし
- **Lorebook レンダリング** ——
  `insertion_order` でソート、無効な entry はスキップ、超過分は末尾を切り詰め。
  Hermes target は `HERMES.md` に、OpenClaw target は `AGENTS.md` の
  managed section に書き込みます。
- **アイデンティティ指令** —— その runtime のローダー優先度が最も高い
  ファイル(Hermes は SOUL.md、OpenClaw は AGENTS.md)に自動注入し、
  runtime 内蔵の「あなたは AI アシスタントです」というフレーミングを
  上書きします。「私は AI です。ロールプレイなら X を演じています」
  のような答えを返さず、キャラクターとして直接答えるようになります。
- **3 層のセキュリティ** —— 可視の信頼バナー、解析時のサニタイズ
  (ゼロ幅文字 / RTL オーバーライド / 制御文字の除去)、
  プロンプトインジェクションカテゴリ別の赤旗パターンスキャン
- **大きなカードの agent 駆動フロー** —— カードのレンダリング結果が
  runtime のファイル単位予算の閾値を超えたら、`import.py` がソース素材を
  ディスクに置き、呼び出し側の agent が自分のコンテキストで V2 カテゴリ
  へ再配置します(子プロセス LLM 呼び出しはありません)。その後
  `finalize.py` が精選 SOUL.md と companion インデックスファイルを
  組み立てます。
- **カードライブラリ** —— `<home>` ディレクトリ(Hermes は `HERMES_HOME`、
  OpenClaw は workspace ディレクトリ)にインポートされたカードに対する
  list / current / switch / delete / restore
- **スナップショット履歴** —— 各 `import` / `switch` / `revert` が
  `cards/.snapshots/` 以下にキャプチャされ、初回インポート前の状態を
  表す特別な `pristine` スナップショットも保存。`revert --to pristine` /
  `--previous` / `--to <id|name>` で履歴を辿れます
- **チャンネル非依存** —— runtime が起動時に読み込むペルソナファイルを
  生成するだけ。runtime が話せるすべての場所で自動的にキャラクターとして
  振る舞います

## よく使うコマンド

先に `SKILL=path/to/skills/soultavern` を設定し、それから:

```bash
# カードのサニティチェック(parse + render + scan、ファイル書き込みなし)
python3 $SKILL/scripts/validate.py --card aldous.png

# レンダリング後の markdown をプレビュー
python3 $SKILL/scripts/import.py --card aldous.png --home ~/.hermes-roleplay --dry-run

# 既存のペルソナを置き換え
python3 $SKILL/scripts/import.py --card alice.png --home ~/.hermes-roleplay --overwrite

# ライブラリ管理
python3 $SKILL/scripts/list.py    --home ~/.hermes-roleplay [--all]
python3 $SKILL/scripts/current.py --home ~/.hermes-roleplay
python3 $SKILL/scripts/switch.py  --card alice --home ~/.hermes-roleplay
python3 $SKILL/scripts/delete.py  --card bob   --home ~/.hermes-roleplay
python3 $SKILL/scripts/restore.py --card bob   --home ~/.hermes-roleplay

# スナップショット履歴(import/switch のたびにキャプチャ)
python3 $SKILL/scripts/history.py --home ~/.hermes-roleplay
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --to pristine
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --previous
python3 $SKILL/scripts/revert.py  --home ~/.hermes-roleplay --to 0003

# カード作者の system_prompt / post_history_instructions を信頼する
# (デフォルトでは untrusted ブロッククォート内にレンダリング)
python3 $SKILL/scripts/import.py ... --trust-system-prompt

# agent が大きなカードの extended/<category>.md を書き終えたら、これで仕上げ
python3 $SKILL/scripts/finalize.py --card aldous --home ~/.hermes-roleplay
```

`switch` / `delete` / `restore` はファイル名でもキャラクター名でも受け取り
ます(解析後の `name` フィールドまたはファイル名 stem に対する大文字小文字
を区別しない前方一致)。

## 動作モード

SoulTavern はカードのレンダリングサイズに応じて 2 つのモードのいずれかを
選びます。閾値は runtime のファイル単位スロットの 75% ——
`--target hermes` は 15,000 文字、`--target openclaw` は 9,000 文字
(詳細は `references/openclaw-target.md`)。

### 小さいカード(レンダリング結果が閾値以下)

`--target hermes` レイアウト:

```
<home>/
├── SOUL.md                          ← レンダリング済みペルソナ
├── HERMES.md                        ← レンダリング済み lorebook
│                                       (カードに character_book がある場合のみ)
└── cards/
    ├── .active.json                 ← 現在アクティブなカードのポインター
    ├── .snapshots/<NNNN>_…/         ← ペルソナファイル履歴
    ├── .trash/                      ← ソフト削除されたカード (delete/restore)
    └── <name>_<ts>.<ext>            ← オリジナルカードのバックアップ
```

`--target openclaw` は `IDENTITY.md` (キャラクターメタデータ)を追加で書き、
lorebook は `HERMES.md` ではなく `AGENTS.md` の managed section として
書き込みます。ファイル単位の詳細は `references/openclaw-target.md`。

### 大きなカード —— agent 駆動

SoulTavern は **独立した LLM を shell out しません。** `import.py` は
ソース素材をディスクに置いて終了コード 2 で抜け、呼び出し側の agent に
8 つの V2 カテゴリへの再配置を依頼します(原文の言葉を忠実に保ち、
ポリシーと衝突する内容は素直にスキップ)。agent がカテゴリファイルを
書き終えたら、`finalize.py` が最終的な SOUL.md(少数の「常時オン」
ピックから)と companion インデックスファイルを組み立てます。

```
<home>/
├── SOUL.md                          ← ピック 3 種: identity + personality + roleplay_guides
├── <companion>                      ← Director's Notes + V2 カテゴリインデックス
│                                       (HERMES.md または AGENTS.md managed section)
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← オリジナルカードのバックアップ
    └── <name>_<ts>/
        ├── source.md                ← スクリプトが agent に渡す素材
        └── extended/                ← V2 カテゴリ
            ├── identity.md          ← 名前、年齢、民族、基本情報             (agent 作成)
            ├── appearance.md        ← 容姿、声、特徴                              (agent 作成)
            ├── personality.md       ← 性格、習慣、口調、クセ                    (agent 作成)
            ├── backstory.md         ← 過去、経歴、人間関係                       (agent 作成)
            ├── scenario.md          ← 会話の冒頭シーン設定                       (agent 作成)
            ├── kinks.md             ← 嗜好(ソースに記述がある場合のみ)         (agent 作成)
            ├── roleplay_guides.md   ← 演じ方の明示的な指示                       (agent 作成)
            ├── examples.md          ← サンプル対話                                  (agent 作成)
            ├── alternate_greetings/01.md, 02.md, ...                              (スクリプト)
            └── lore/<entry-slug>.md ← character_book の各エントリ                (スクリプト)
```

空のカテゴリはファイルが書かれず単純にスキップされます(agent が「この
カテゴリに入れる内容はない」と判断したか、または拒否した — どちらも
companion インデックス上で「ファイルが見当たらない」こととして
観察できる信号です)。

モデルは会話の冒頭で SOUL.md と companion ファイルのみを静的に読み込み、
詳細が必要になったときだけ対応する `extended/...md` を開きます。
Hermes は `HERMES.md` を cwd から読むため、runtime を `$HERMES_HOME`
から起動する必要があります(HERMES.md がカテゴリ別ファイルへの
インデックスを兼ねており、見つかる場所にある必要がある)。

完全な手順(`finalize` ステップと失敗モードを含む)は
[`skills/soultavern/references/oversized-cards.md`](skills/soultavern/references/oversized-cards.md)
を参照。

## SoulTavern が書き込むファイル / 絶対に書き込まないファイル

**書き込み(`<home>` 内のみ):** 上のレイアウト。爆発半径はそれだけ。

**絶対に書き込まない(`--target hermes`):**

- `AGENTS.md` —— Hermes のローダー優先度により HERMES.md に隠される
- `MEMORY.md`、`USER.md` —— 稼働中エージェントのメモリツールが管理
- `CLAUDE.md`、`.cursorrules` —— 他ツールの領分
- ランタイムにおける `<home>` 外のあらゆるファイル
- runtime 設定 / チャンネル許可リスト / `platform_toolsets` エントリ

**書き込み(`--target openclaw`):** SOUL.md(完全置換)、AGENTS.md
(`<!-- BEGIN soultavern:character -->` マーカー間のみ —— マーカー外の
ユーザー記述はそのまま保持)、IDENTITY.md(完全置換)。

`<home>` を完全にクリーンアップ:
`rm -rf <home>/{SOUL.md,HERMES.md,IDENTITY.md,cards}`、加えて
AGENTS.md から soultavern managed section を削除。他には何も漏れません。

## ドキュメント

skill 自体がドキュメント;`SKILL.md` と `references/` 配下に
オペレーター向けの完全な解説があります。

- [`skills/soultavern/SKILL.md`](skills/soultavern/SKILL.md) —
  import + ライブラリ管理(list / current / switch / delete / restore /
  history / revert)を 1 つの SKILL.md に統合

**リファレンス文書**

- [`v2-spec-summary.md`](skills/soultavern/references/v2-spec-summary.md) — V2 カードフィールド早見表
- [`field-mapping.md`](skills/soultavern/references/field-mapping.md) — V2 → markdown の正確なルール
- [`usage-recipes.md`](skills/soultavern/references/usage-recipes.md) — よく使うワークフローと注意点
- [`security.md`](skills/soultavern/references/security.md) — 脅威モデル + サニタイザー層
- [`oversized-cards.md`](skills/soultavern/references/oversized-cards.md) — 大きなカードの agent 駆動分配フロー
- [`library-layout.md`](skills/soultavern/references/library-layout.md) — `<home>/cards/` schema、スナップショット、`--card` 解決

## リポジトリレイアウト

```
SoulTavern/
├── tests/                         pytest スイート(リアルカード smoke を含む)
├── examples/                      ローカルのサードパーティカード(gitignore)
├── pyproject.toml                 dev ツール設定(pytest / ruff / mypy)
└── skills/                        skill ツリー
    └── soultavern/                1 つの skill: import + ライブラリ管理
        ├── SKILL.md               LLM 向けのエントリードキュメント
        ├── scripts/               操作ごとのエントリースクリプト + エンジン Python パッケージ
        │   ├── import.py  switch.py  list.py  …    LLM が直接呼ぶ薄いシム
        │   └── soultavern/        Python パッケージ(stdlib のみ)
        │       └── targets/       runtime 別アダプター(hermes / openclaw / generic)
        ├── references/            8 件の参考文書
        └── assets/                サンプル V2 カード
```

> **v2.0.0 破壊的変更。** `soultavern` CLI は廃止。すべての操作は
> `skills/soultavern/scripts/` 配下のスクリプトです。Python パッケージは
> `src/soultavern/` から `skills/soultavern/scripts/soultavern/` へ移動。
> wheel 配布、install.sh、`hermes-tavern` 後方互換エイリアスもすべて削除
> しました。完全な移行手順は [CHANGELOG.md](CHANGELOG.md#200) を参照。

> **v1.0.0 改名。** v1.0 以前は **HermesTavern**(単一 target、
> Hermes-Agent 専用)という名前でした。v1.0 で **SoulTavern** に
> リブランドし、複数 target サポートを導入しました。

> **v0.5.0 注記。** さらに以前のバージョンではライブラリ管理を別 skill
> `hermes-tavern-cards` として配布していました。v0.5.0 で本 skill
> に統合済みです。

`skills/` サブディレクトリは `openai/skills` および `anthropics/skills` で
使われている `path: "skills/"` 規約に揃えてあるので、tap-style の
skill 発見をサポートする runtime であれば追加設定なしに動きます。
各 skill フォルダは標準の `references/` / `scripts/` /
`assets/` レイアウトを使用 —— コンテンツのあるカテゴリだけが配置されます。

## 既知の制限

- **キーワードトリガー型 lorebook injection はサポートしません。**
  すべての entry は always-on としてレンダリングされます。
  これは忠実度を簡潔さで取引するもので、長コンテキストのモデルでは問題
  ありません;サイズが大きい lorebook はゲーティングではなく agent
  駆動の extended-files フローで扱います。
- **1 つの runtime インスタンスでの複数キャラチャットは未サポート。**
  キャラクターごとに別の `<home>` を使ってください。
- **チャンネルレベルの安全制御はありません。** runtime 側で設定して
  ください(Hermes の `platform_toolsets`、許可リスト、レート制限など)。
  SoulTavern はペルソナファイルを書くだけです。
- **ライブ編集はサポートしません。** runtime はセッション開始時に
  system prompt をキャッシュします。ペルソナファイルへの編集は
  次回セッションで反映されます(Hermes ならセッション中に `/reset`
  でも反映可能)。

## 既知の問題

- **一部の IM クライアントは PNG アップロード時に画像を再エンコードし、
  キャラクターカードのデータを破壊します。** SillyTavern V2 カードは実際の
  ペイロードを PNG の `tEXt` チャンクに格納しています; IM が画像を書き換える
  (リサイズ、メタデータ除去、JPEG サムネイル化など)とそのチャンクが失われ、
  SoulTavern はファイルを解析できなくなります。**回避策:** PNG を zip に
  してからアップロードしてください(`zip aldous.zip aldous.png`)。
  IM はバイナリ blob として扱い、バイトを変更しません。runtime は
  zip を展開してインポートできます。
- **ポリシー制限の強い agent では、大きなカードのカテゴリ分けが部分的に
  終わることがあります。** カードが runtime の閾値(hermes は 15k、
  openclaw は 9k)を超えると、SoulTavern はソース素材をディスクに置き、
  呼び出し側の agent にカテゴリ分けを依頼します。ポリシーで制限された
  agent は一部のカテゴリ(たとえば `kinks.md`)の作成を拒否することが
  あり、その場合該当カテゴリは最終的な companion インデックスに現れません
  —— キャラクター自体は読み込まれますが、agent が残してくれた範囲の
  内容になります。より広い範囲を取りたい場合は、別モデルの agent で
  `source.md` を再処理してから `finalize.py` を再実行してください。

## 開発

```bash
git clone https://github.com/imphillip/SoulTavern.git && cd SoulTavern
python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"      # pytest / ruff / mypy のみ — ランタイム依存はゼロ

pytest                    # 全スイートを実行
pytest -k staging         # サブセットを実行
pytest tests/test_real_cards_smoke.py   # リアルカード smoke(カードがなければ自動 skip)
```

`tests/conftest.py` が `skills/soultavern/scripts/` を `sys.path` に追加するため、
`from soultavern.parse import load_card` のような import は
`pip install -e .` なしで動きます。ランタイムパッケージは
サードパーティ依存ゼロ —— `[dev]` はテスト・lint ツールチェーンのみです。

自前のカードでリアルカード smoke を回すには、`examples/.local/` に
置いてください。このディレクトリは gitignore されています —— コミュニティ
カードのライセンス / サイズ / 内容は様々で再配布できないため、
ローカルに留めます。

`tests/` スイートは parse、render、substitute、sanitize、scan、classify、
staging、extended、finalize、library、CLI、エンドツーエンドパイプラインを
カバーしています。グリーンを目指してください。

## コントリビューション

PR 歓迎です。提出前に:

1. 変更内容に対するテストを `tests/` 配下に追加または更新。
2. `pytest` を実行してグリーンを維持。
3. カード → markdown のコントラクトを変更した場合は、
   `skills/soultavern/references/field-mapping.md` を更新して
   仕様とコードを一致させる。
4. `scripts/*.py` のいずれかにフラグを追加した場合は、関連する
   `SKILL.md` および README の「よく使うコマンド」に記載。

設計議論、バグレポート、機能リクエストの issue も歓迎です。

## 使用例

[agentbox.id](https://agentbox.id) の `soul-loader`(Hermes と OpenClaw
ランタイム向けの agentbox 公認の魂読み込みフロー)は、SoulTavern を
裏側のエンジンとして呼び出します。詳細は
[`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md)
を参照。

## ライセンス

[MIT](LICENSE) — © 2026 SoulTavern contributors.
