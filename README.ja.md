# HermesTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> Hermes エージェント上で SillyTavern キャラクターを動かす。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

HermesTavern は SillyTavern V2 キャラクターカード(`.png` / `.json` /
`.yaml`)を、[Hermes-Agent](https://github.com/NousResearch/hermes-agent) が
起動時にアイデンティティとプロジェクトコンテキストとして読み込む 2 つの
マークダウンファイル、`SOUL.md` と `HERMES.md` に変換するワンショット
インポーターです。

ミドルウェアもパッチもリレーも不要。カードを投入し、マークダウンを取り出し、
Hermes に向ければエージェントはキャラクターになりきります——すでに設定済みの
あらゆるゲートウェイ(CLI、メール、Telegram、Discord、Slack、…)を横断して。

**系譜:** `TavernAI` → `SillyTavern` → **`HermesTavern`**

---

## 使い方

Hermes はそれ自体が成熟した AI エージェントです——意図を理解し、添付を取得し、
適切なツールを呼び出す能力を備えています。HermesTavern をインストールしさえ
すれば、ユーザー側の UX は完全に会話ベース。覚えるべきコマンドはありません。

Hermes チャット(Telegram、Discord、QQ、メール——Hermes が話せるあらゆる
チャンネル)で、カードファイルをアップロードし、自然な日本語で伝えるだけ:

> _[aldous.png 添付]_ このキャラクターをインストールして

> alice に切り替えて

> すべてのキャラを忘れて、デフォルトの Hermes に戻して

それで全部です。Hermes は意図を解釈し、裏で `hermes-tavern` を呼び出し、
変更を反映するための `/new` または `/reset` の実行をユーザーに促します。
曖昧な点があれば普段の言葉で言い直すだけ——あとは Hermes が処理します。

## インストール

ファイルを 1 回アップロードするだけ。Hermes が動いていればターミナルは不要:

```bash
git clone https://github.com/imphillip/hermes-tavern.git
cd hermes-tavern && zip -r hermes-tavern-skills.zip skills/
```

Hermes チャットで `hermes-tavern-skills.zip` をアップロードし、
**「この skill をインストールして」** と伝えてください。
個別のサブ skill ではなく `skills/` ディレクトリ全体を zip にしてください——
Hermes は `skills/<name>/SKILL.md` のレイアウトを期待しており、
`skills/hermes-tavern/assets/` に同梱された wheel を使って `hermes-tavern`
CLI を PATH に通します。

これ以降、すべてのやり取りは上で示した「アップロードして話す」だけです。

### あるいは Hermes hub 経由

Hermes に hub の `tap` システムが設定されている場合:

```bash
hermes skills tap add imphillip/hermes-tavern
hermes skills install hermes-tavern hermes-tavern-cards
```

### Bootstrap: ホスト上で CLI を直接インストール

Hermes 自体がまだ立ち上がっていない、もしくは別ホストに CLI を入れたい
場合のみ必要です(新しい Hermes マシンの初期セットアップなど):

```bash
git clone https://github.com/imphillip/hermes-tavern.git && cd hermes-tavern
bash skills/hermes-tavern/scripts/install.sh
```

冪等です——`pipx` → `uv tool` → `~/.local/share/hermes-tavern-venv` 専用
venv + `~/.local/bin` shim、の順に試行します。`HERMES_TAVERN_VENV` /
`HERMES_TAVERN_BIN` でパスを上書き可能。`hermes-tavern` が PyPI に公開
されたら、これは `pipx install hermes-tavern` に置き換わり、
同梱 wheel もなくなります。

### 必要環境

- Python ≥ 3.10
- 大きなカードに蒸留を使いたい場合、稼働中の
  [`hermes`](https://github.com/NousResearch/hermes-agent) CLI
  (デフォルト `--distill-cmd "hermes -q"`、`--distill-cmd` で上書きするか
  `--no-distill` でスキップ)

---

## なぜ作ったか

Hermes は起動時に `SOUL.md`(独立したアイデンティティスロット)と
`HERMES.md`(cwd 相対のプロジェクトコンテキストスロット)を system prompt に
自動読み込みします。唯一足りなかったのは、SillyTavern V2 schema、プレース
ホルダー文法(`{{char}}`、`{{user}}`、`<BOT>`、`<USER>`)、ロアブック
レイアウトを尊重するコンバーターです。それが HermesTavern の役割です。

意図的にやらないこと:

- Hermes へのパッチ
- ミドルウェア / リレーの作成
- チャンネル設定の改変(`platform_toolsets`、許可リスト、…)
- Hermes プロセスの起動・監視
- `AGENTS.md` / `MEMORY.md` / `USER.md` / `CLAUDE.md` への書き込み

## 機能

- **V2 + V1 + PNG + YAML 解析** —— 野生の SillyTavern が出すあらゆる
  コンテナ形式に対応
- **プレースホルダー置換** —— `{{char}}` / `{{user}}` に加えてレガシーの
  `<BOT>` / `<USER>`、大文字小文字を区別せず、再帰なし
- **Lorebook → HERMES.md レンダリング** ——
  `insertion_order` でソート、無効な entry はスキップ、超過分は末尾を切り詰め
- **アイデンティティ指令** —— SOUL.md の先頭に自動注入され、
  hermes 内蔵の「あなたは AI アシスタントです」というフレーミングを
  上書きします。「私は AI です。ロールプレイなら X を演じています」のような
  答えを返さず、キャラクターとして直接答えるようになります
- **3 層のセキュリティ** —— 可視の信頼バナー、解析時のサニタイズ
  (ゼロ幅文字 / RTL オーバーライド / 制御文字の除去)、
  プロンプトインジェクションカテゴリ別の赤旗パターンスキャン
- **蒸留パイプライン** —— カードのレンダリング結果が Hermes 20k スロットの
  75% を超えたら、`hermes -q` を shell out して prompt 投入分を圧縮し、
  オリジナルのコンテンツはランタイム取得用にディスクに展開
- **カードライブラリ** —— `HERMES_HOME` にインポートされたカードに対する
  list / current / switch / delete / restore
- **スナップショット履歴** —— 各 `import` / `switch` / `revert` が
  `cards/.snapshots/` 以下にキャプチャされ、HermesTavern 導入前の状態を
  表す特別な `pristine` スナップショットも保存。`revert --to pristine` /
  `--previous` / `--to <id|name>` で履歴を辿れます
- **チャンネル非依存** —— Hermes が起動時に読み込むペルソナファイルを
  生成するだけ。Hermes が話せるすべての場所で自動的にキャラクターとして
  振る舞います

## よく使うコマンド

```bash
# カードのサニティチェック(parse + render + scan、ファイル書き込みなし)
hermes-tavern validate --card aldous.png

# レンダリング後の markdown をプレビュー
hermes-tavern import --card aldous.png --home ~/.hermes-roleplay --dry-run

# 既存のペルソナを置き換え
hermes-tavern import --card alice.png --home ~/.hermes-roleplay --overwrite

# ライブラリ管理
hermes-tavern list    --home ~/.hermes-roleplay [--all]
hermes-tavern current --home ~/.hermes-roleplay
hermes-tavern switch  --card alice --home ~/.hermes-roleplay
hermes-tavern delete  --card bob   --home ~/.hermes-roleplay
hermes-tavern restore --card bob   --home ~/.hermes-roleplay

# SOUL.md / HERMES.md スナップショット履歴(import/switch のたびにキャプチャ)
hermes-tavern history --home ~/.hermes-roleplay
hermes-tavern revert  --home ~/.hermes-roleplay --to pristine     # カード読み込み前に戻る
hermes-tavern revert  --home ~/.hermes-roleplay --previous        # 1 つ前へ
hermes-tavern revert  --home ~/.hermes-roleplay --to 0003

# カード作者の system_prompt / post_history_instructions を信頼する
# (デフォルトでは untrusted ブロッククォート内にレンダリング)
hermes-tavern import ... --trust-system-prompt

# 大きなカードの蒸留を無効化(本来の予算超過エラーを表面化)
hermes-tavern import ... --no-distill

# 別のコマンドで蒸留
hermes-tavern import ... --distill-cmd "claude -p"
```

`switch` / `delete` / `restore` はファイル名でもキャラクター名でも受け取り
ます(解析後の `name` フィールドまたはファイル名 stem に対する大文字小文字
を区別しない前方一致)。

## 動作モード

HermesTavern はカードのレンダリングサイズに応じて 2 つのモードのいずれかを
選びます。閾値は Hermes 20k スロットの 75% —— つまり 15,000 文字 ——
SOUL.md / HERMES.md の **どちらか** がこれを超えると切り替わります。

### 通常モード(レンダリング結果が各スロット ≤ 15k)

```
<HERMES_HOME>/
├── SOUL.md                          ← レンダリング済みペルソナ
├── HERMES.md                        ← レンダリング済み lorebook
│                                       (カードに character_book がある場合のみ)
└── cards/
    ├── .active.json                 ← 現在アクティブなカードのポインター
    ├── .snapshots/<NNNN>_…/         ← SOUL.md / HERMES.md 履歴
    ├── .trash/                      ← ソフト削除されたカード (delete/restore)
    └── <name>_<ts>.<ext>            ← オリジナルカードのバックアップ
```

### 蒸留モード(SOUL または HERMES が > 15k)

HermesTavern は設定済みの Hermes CLI(デフォルト `hermes -q`)を shell out
経由で呼び、レンダリング結果を一回限りの LLM 圧縮にかけたうえで、
**オリジナルのコンテンツ全体** をフィールドごとにディスクに配置し、
モデルがランタイムに取得できるようにします。

```
<HERMES_HOME>/
├── SOUL.md                          ← LLM 蒸留済みペルソナ(コンパクト)
├── HERMES.md                        ← 蒸留済み lore + 拡張ファイルのインデックス
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← オリジナルカードのバックアップ
    └── <name>_<ts>/
        └── extended/                ← オリジナルの全コンテンツ(フィールド別)
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

モデルは会話の冒頭で SOUL.md と HERMES.md のみを静的に読み込み、
詳細が必要になったときだけ対応する `extended/...md` を開きます——
だからこそ蒸留モードでは `cd $HERMES_HOME` がより重要になります
(HERMES.md がフィールド別ファイルへのインデックスを兼ねるため)。

蒸留を無効化する場合は `--no-distill`(本来の予算超過エラーを表面化)。
蒸留コマンドの上書きは `--distill-cmd "<command>"`。完全なパイプラインは
[`skills/hermes-tavern/references/distillation.md`](skills/hermes-tavern/references/distillation.md)
を参照。

## HermesTavern が書き込むファイル / 絶対に書き込まないファイル

**書き込み(`<HERMES_HOME>` 内のみ):** 上のレイアウト。爆発半径はそれだけ。

**絶対に書き込まない:**

- `AGENTS.md` —— Hermes のローダー優先度により HERMES.md に隠される
- `MEMORY.md`、`USER.md` —— 稼働中エージェントのメモリツールが管理
- `CLAUDE.md`、`.cursorrules` —— 他ツールの領分
- ランタイムにおける `<HERMES_HOME>` 外のあらゆるファイル
- Hermes 設定 / チャンネル許可リスト / `platform_toolsets` エントリ

`HERMES_HOME` を完全にクリーンアップ:
`rm -rf <home>/{SOUL.md,HERMES.md,cards}` —— 他には何も漏れません。

## ドキュメント

2 つの skill はそれ自体がドキュメント;`SKILL.md` と `references/` 配下に
オペレーター向けの完全な解説があります。

**Skills**

- [`skills/hermes-tavern/SKILL.md`](skills/hermes-tavern/SKILL.md) —
  import & validate
- [`skills/hermes-tavern-cards/SKILL.md`](skills/hermes-tavern-cards/SKILL.md) —
  list / current / switch / delete / restore

**リファレンス文書 (loader skill)**

- [`v2-spec-summary.md`](skills/hermes-tavern/references/v2-spec-summary.md) — V2 カードフィールド早見表
- [`field-mapping.md`](skills/hermes-tavern/references/field-mapping.md) — V2 → markdown の正確なルール
- [`usage-recipes.md`](skills/hermes-tavern/references/usage-recipes.md) — よく使うワークフローと注意点
- [`security.md`](skills/hermes-tavern/references/security.md) — 脅威モデル + サニタイザー層
- [`distillation.md`](skills/hermes-tavern/references/distillation.md) — 大きなカード向けパイプライン

**リファレンス文書 (cards skill)**

- [`library-layout.md`](skills/hermes-tavern-cards/references/library-layout.md) — `<HERMES_HOME>/cards/` schema、`--card` 解決

## リポジトリレイアウト

```
hermes-tavern/
├── src/hermes_tavern/             Python パッケージ(エンジン本体; PyPI 公開までは同梱 wheel)
├── tests/                         pytest スイート(リアルカード smoke を含む)
├── examples/                      ローカルのサードパーティカード(gitignore)
└── skills/                        Hermes hub から発見可能な skill ツリー
    ├── hermes-tavern/             Skill 1: import & validate
    │   ├── SKILL.md
    │   ├── references/            5 件の参考文書
    │   ├── scripts/               skill エントリーラッパー + install.sh
    │   └── assets/                同梱 wheel + サンプル V2 カード
    └── hermes-tavern-cards/       Skill 2: ライブラリ管理(hermes-tavern 依存)
        ├── SKILL.md
        ├── references/            library-layout 文書
        └── scripts/               skill エントリーラッパー
```

`skills/` サブディレクトリは `openai/skills` および `anthropics/skills` で
使われている `path: "skills/"` 規約に揃えてあるので、
`hermes skills tap add imphillip/hermes-tavern` だけで追加設定なしに
動きます。各 skill フォルダは標準の `references/` / `scripts/` /
`assets/` レイアウトを使用 —— コンテンツのあるカテゴリだけが配置されます。

## 既知の制限

- **キーワードトリガー型 lorebook injection はサポートしません。**
  すべての entry は always-on としてレンダリングされます。
  これは忠実度を簡潔さで取引するもので、長コンテキストのモデルでは問題
  ありません;サイズが大きい lorebook はゲーティングではなく蒸留で扱います。
- **1 つの Hermes インスタンスでの複数キャラチャットは未サポート。**
  キャラクターごとに別の `HERMES_HOME` を使ってください。
- **チャンネルレベルの安全制御はありません。** Hermes 側で設定してください
  (`platform_toolsets`、許可リスト、レート制限)。HermesTavern は
  ペルソナファイルを書くだけです。
- **ライブ編集はサポートしません。** Hermes はセッション開始時に
  system prompt をキャッシュします。`SOUL.md` / `HERMES.md` への編集は
  次回セッションか、hermes 内での `/reset` の後に反映されます。

## 既知の問題

- **一部の IM クライアントは PNG アップロード時に画像を再エンコードし、
  キャラクターカードのデータを破壊します。** SillyTavern V2 カードは実際の
  ペイロードを PNG の `tEXt` チャンクに格納しています; IM が画像を書き換える
  (リサイズ、メタデータ除去、JPEG サムネイル化など)とそのチャンクが失われ、
  HermesTavern はファイルを解析できなくなります。**回避策:** PNG を zip に
  してからアップロードしてください(`zip aldous.zip aldous.png`)。
  IM はバイナリ blob として扱い、バイトを変更しません。Hermes は zip を
  展開してインポートできます。
- **大きなカードの蒸留は、コンテンツ制限の強いモデルで停滞することが
  あります。** カードが 15k 閾値を超えると、HermesTavern は `hermes -q` を
  shell out で呼び出して LLM 圧縮を行います。カードに成人向け、もしくは
  コンテンツポリシーに触れる内容が含まれていて、かつ基盤 LLM の検閲が強い
  場合、この呼び出しが目に見えて遅くなる(リトライ、ストリーミング遅延、
  ハード拒否)ことがあります——フリーズしたように見えるほど。
  HermesTavern 側にきれいな修正はありません: こうしたカードについては
  Hermes をより制限の緩いモデルに向けてください。

## 開発

```bash
git clone https://github.com/imphillip/hermes-tavern.git && cd hermes-tavern
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                    # 全スイートを実行
pytest -k distill         # サブセットを実行
pytest tests/test_real_cards_smoke.py   # リアルカード smoke(カードがなければ自動 skip)
```

自前のカードでリアルカード smoke を回すには、`examples/.local/` に
置いてください。このディレクトリは gitignore されています —— コミュニティ
カードのライセンス / サイズ / 内容は様々で再配布できないため、
ローカルに留めます。

`tests/` スイートは parse、render、substitute、sanitize、scan、extended、
distill(LLM mock)、library、CLI、エンドツーエンドパイプラインをカバー
しています。グリーンを目指してください;mock していない subprocess テストは
tempdir に書き出した小さな fake `hermes` シェルスクリプトを使います。

## コントリビューション

PR 歓迎です。提出前に:

1. 変更内容に対するテストを `tests/` 配下に追加または更新。
2. `pytest` を実行してグリーンを維持。
3. カード → markdown のコントラクトを変更した場合は、
   `skills/hermes-tavern/references/field-mapping.md` を更新して
   仕様とコードを一致させる。
4. CLI flag を追加した場合は、関連する `SKILL.md` および README の
   「よく使うコマンド」に記載。

設計議論、バグレポート、機能リクエストの issue も歓迎です。

## 使用例

[agentbox.id](https://agentbox.id) の `soul-loader`(agentbox の魂読み込みフロー)は、
Hermes ランタイム上で HermesTavern を内部的にインストール・呼び出します。
詳細は [`agentbox.id/setup/soul-loader.md`](https://agentbox.id/setup/soul-loader.md)
を参照。

## ライセンス

[MIT](LICENSE) — © 2026 HermesTavern contributors.
