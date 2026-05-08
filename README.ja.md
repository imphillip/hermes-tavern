# SoulTavern

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

> SOUL.md を読み込むあらゆる agent runtime で SillyTavern キャラクターを動かす。

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

SoulTavern は SillyTavern V2 キャラクターカード(`.png` / `.json` /
`.yaml`)を、agent runtime が起動時に読み込むマークダウンシステム
プロンプトファイルへ変換するワンショットインポーターです。v1.0 は 2 つの
target を提供: `--target hermes`
([Hermes-Agent](https://github.com/NousResearch/hermes-agent) 用の
`SOUL.md` + `HERMES.md` を出力)と `--target openclaw`
([OpenClaw](https://github.com/imphillip/openclaw) workspace 用の
`SOUL.md` + `AGENTS.md` managed-section + `IDENTITY.md` を出力)。

ミドルウェアもパッチもリレーも不要。カードを投入し、マークダウンを取り出し、
agent に向ければキャラクターになりきります——すでに設定済みのあらゆる
ゲートウェイ(CLI、メール、Telegram、Discord、Slack、…)を横断して。

**系譜:** `TavernAI` → `SillyTavern` → `HermesTavern` → **`SoulTavern`**

> SoulTavern v1.0 は HermesTavern(≤ v0.5.x)の改名 + 一般化版です。
> CLI バイナリ名は `soultavern` に変更され、旧名 `hermes-tavern` は
> 後方互換エイリアスとして残ります。デフォルトの `--target hermes` は
> v0.5.x の動作を完全に再現します。

---

## ビジョン: HermesTavern から SoulTavern へ

HermesTavern は、より大きな方向性の最初の具体例です——「セッション
開始時に永続的な人格ファイルを読み込む」あらゆる agent runtime に、
SillyTavern キャラクターカードのエコシステム全体を接続可能にする、
というのが大きな方向性です。

これを **SoulTavern** として一般化しました: 複数 target に対応する
アダプター。v1.0 では 2 つの target が稼働: `--target hermes`
(デフォルト; v0.5.x の動作変更なし)と `--target openclaw`
(OpenClaw workspace に `SOUL.md` + `AGENTS.md` managed-section +
`IDENTITY.md` を書き込む)。汎用 `--target generic` フォールバックは
スケルトンとして登録済みで、後続リリースで完成します。

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
   `AGENTS.md`)、(b) ペルソナファイルの先頭に **IDENTITY DIRECTIVE**
   を注入し、その runtime のデフォルト「私は AI アシスタントです」
   フレーミングを抑え込む。(b) が要——抑えられないと、agent は魂の
   衣を被っただけの自分自身のままです。

3. **CLI は決定的処理、LLM 仕事は agent に。** Python ツールは独立
   した LLM へ shell out しません(v0.4.0 で踏んだ轍、v0.4.5 で
   修正済み)。カードが常時コンテキストの容量を超えた場合、CLI は
   `source.md` をディスクに置き、終了コード 2 で抜けます;呼び出し
   側の agent が自身のコンテキストで自身のファイルツールを用いて
   V2 分類を実行します。これによりツールは LLM CLI のバージョン
   進化に依存せず、agent は第三者ファイルを扱う際の信頼姿勢を
   そのまま適用できます——ポリシーと衝突する内容は正々堂々と
   拒否でき、欠落はインデックスで可視化される(これは誠実なシグナル
   であり、密かな書き換えではありません)。

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

**最も簡単な方法** —— [最新リリース](https://github.com/imphillip/SoulTavern/releases/latest)
からビルド済みの zip をダウンロードします:

```bash
curl -LO https://github.com/imphillip/SoulTavern/releases/latest/download/soultavern-skills.zip
```

(ブラウザから Releases ページ経由でも取得できます。)

そのうえで Hermes チャットに `soultavern-skills.zip` をアップロードし、
**「この skill をインストールして」** と伝えてください。zip に同梱された wheel が
`soultavern` CLI を自動的に PATH に通します。

これ以降、すべてのやり取りは上で示した「アップロードして話す」だけです。

### あるいは HEAD からビルド

未リリースの変更を試したい場合(例えば `main` ブランチを追跡したいとき):

```bash
git clone https://github.com/imphillip/SoulTavern.git
cd SoulTavern && zip -r soultavern-skills.zip skills/
```

個別のサブ skill ではなく `skills/` ディレクトリ全体を zip にしてください——
Hermes は `skills/<name>/SKILL.md` のレイアウトを期待しています。
そのうえで上記と同じ手順でアップロードしてください。

### あるいは Hermes hub 経由

Hermes に hub の `tap` システムが設定されている場合:

```bash
hermes skills tap add imphillip/SoulTavern
hermes skills install soultavern
```

### Bootstrap: ホスト上で CLI を直接インストール

Hermes 自体がまだ立ち上がっていない、もしくは別ホストに CLI を入れたい
場合のみ必要です(新しい Hermes マシンの初期セットアップなど):

```bash
git clone https://github.com/imphillip/SoulTavern.git && cd SoulTavern
bash skills/soultavern/scripts/install.sh
```

冪等です——`pipx` → `uv tool` → `~/.local/share/soultavern-venv` 専用
venv + `~/.local/bin` shim、の順に試行します。`SOULTAVERN_VENV` /
`SOULTAVERN_BIN` でパスを上書き可能。`hermes-tavern` が PyPI に公開
されたら、これは `pipx install soultavern` に置き換わり、
同梱 wheel もなくなります。

### アンインストール

skill(プロンプトファイル)と CLI(システムバイナリ)は別レイヤーです。
hub のコマンドは前者だけを扱います:

```bash
bash skills/soultavern/scripts/uninstall.sh   # CLI を削除; --dry-run でプレビュー
hermes skills uninstall hermes-tavern            # skill を削除
```

アンインストーラは pipx / uv tool / 専用 venv を自動判別し、
任意のパスは触りません。また `<HERMES_HOME>/` 内のデータ
(カードライブラリ、SOUL.md、スナップショット —— これらは個人
コンテンツであり、インストール成果物ではありません)も保持します。

### 必要環境

- Python ≥ 3.10
- 大きなカードの処理は、呼び出し側の agent(Hermes 自身、もしくは
  インポートを駆動している任意の agent)が担当します。CLI が
  `source.md` をディスクに置き、agent が自分のファイルツールで
  カテゴリ別ファイルへ書き分けます。独立した LLM CLI を shell out
  することはありません。

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
- **大きなカードの agent 駆動フロー** —— カードのレンダリング結果が
  Hermes 20k スロットの 75% を超えたら、`import` がソース素材を
  ディスクに置き、呼び出し側の agent が自分のコンテキストで V2 カテゴリ
  へ再配置します(子プロセス LLM 呼び出しはありません)。その後
  `soultavern finalize` が精選 SOUL.md とインデックス化された
  HERMES.md を組み立てます。
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
soultavern validate --card aldous.png

# レンダリング後の markdown をプレビュー
soultavern import --card aldous.png --home ~/.hermes-roleplay --dry-run

# 既存のペルソナを置き換え
soultavern import --card alice.png --home ~/.hermes-roleplay --overwrite

# ライブラリ管理
soultavern list    --home ~/.hermes-roleplay [--all]
soultavern current --home ~/.hermes-roleplay
soultavern switch  --card alice --home ~/.hermes-roleplay
soultavern delete  --card bob   --home ~/.hermes-roleplay
soultavern restore --card bob   --home ~/.hermes-roleplay

# SOUL.md / HERMES.md スナップショット履歴(import/switch のたびにキャプチャ)
soultavern history --home ~/.hermes-roleplay
soultavern revert  --home ~/.hermes-roleplay --to pristine     # カード読み込み前に戻る
soultavern revert  --home ~/.hermes-roleplay --previous        # 1 つ前へ
soultavern revert  --home ~/.hermes-roleplay --to 0003

# カード作者の system_prompt / post_history_instructions を信頼する
# (デフォルトでは untrusted ブロッククォート内にレンダリング)
soultavern import ... --trust-system-prompt

# agent が大きなカードの extended/<category>.md を書き終えたら、これで仕上げ
soultavern finalize --card aldous --home ~/.hermes-roleplay
```

`switch` / `delete` / `restore` はファイル名でもキャラクター名でも受け取り
ます(解析後の `name` フィールドまたはファイル名 stem に対する大文字小文字
を区別しない前方一致)。

## 動作モード

HermesTavern はカードのレンダリングサイズに応じて 2 つのモードのいずれかを
選びます。閾値は Hermes 20k スロットの 75% —— つまり 15,000 文字 ——
SOUL.md / HERMES.md の **どちらか** がこれを超えると切り替わります。

### 小さいカード(レンダリング結果が各スロット ≤ 15k)

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

### 大きなカード(SOUL または HERMES が > 15k)—— agent 駆動

HermesTavern は **独立した LLM を shell out しません。** `import` は
ソース素材をディスクに置いて終了コード 2 で抜け、呼び出し側の agent に
8 つの V2 カテゴリへの再配置を依頼します(原文の言葉を忠実に保ち、
ポリシーと衝突する内容は素直にスキップ)。agent がカテゴリファイルを
書き終えたら、`soultavern finalize` が最終的な SOUL.md(少数の
「常時オン」ピックから)と HERMES.md(カテゴリインデックス)を
組み立てます。

```
<HERMES_HOME>/
├── SOUL.md                          ← ピック 3 種: identity + personality + roleplay_guides
├── HERMES.md                        ← Director's Notes + V2 カテゴリインデックス
└── cards/
    ├── .active.json
    ├── <name>_<ts>.<ext>            ← オリジナルカードのバックアップ
    └── <name>_<ts>/
        ├── source.md                ← CLI が agent に渡すための素材
        └── extended/                ← V2 カテゴリ
            ├── identity.md          ← 名前、年齢、民族、基本情報             (agent 作成)
            ├── appearance.md        ← 容姿、声、特徴                              (agent 作成)
            ├── personality.md       ← 性格、習慣、口調、クセ                    (agent 作成)
            ├── backstory.md         ← 過去、経歴、人間関係                       (agent 作成)
            ├── scenario.md          ← 会話の冒頭シーン設定                       (agent 作成)
            ├── kinks.md             ← 嗜好(ソースに記述がある場合のみ)         (agent 作成)
            ├── roleplay_guides.md   ← 演じ方の明示的な指示                       (agent 作成)
            ├── examples.md          ← サンプル対話                                  (agent 作成)
            ├── alternate_greetings/01.md, 02.md, ...                              (CLI 作成)
            └── lore/<entry-slug>.md ← character_book の各エントリ                (CLI 作成)
```

空のカテゴリはファイルが書かれず単純にスキップされます(agent が「この
カテゴリに入れる内容はない」と判断したか、または拒否した — どちらも
HERMES.md インデックス上で「ファイルが見当たらない」こととして
観察できる信号です)。

モデルは会話の冒頭で SOUL.md と HERMES.md のみを静的に読み込み、
詳細が必要になったときだけ対応する `extended/...md` を開きます ——
だからこそ大きなカードのモードでは `cd $HERMES_HOME` がより重要になります
(HERMES.md がカテゴリ別ファイルへのインデックスを兼ねるため)。

完全な手順(`finalize` ステップと失敗モードを含む)は
[`skills/soultavern/references/oversized-cards.md`](skills/soultavern/references/oversized-cards.md)
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
- [`library-layout.md`](skills/soultavern/references/library-layout.md) — `<HERMES_HOME>/cards/` schema、スナップショット、`--card` 解決

## リポジトリレイアウト

```
hermes-tavern/
├── src/hermes_tavern/             Python パッケージ(エンジン本体; PyPI 公開までは同梱 wheel)
├── tests/                         pytest スイート(リアルカード smoke を含む)
├── examples/                      ローカルのサードパーティカード(gitignore)
└── skills/                        Hermes hub から発見可能な skill ツリー
    └── hermes-tavern/             1 つの skill: import + ライブラリ管理
        ├── SKILL.md
        ├── references/            6 件の参考文書
        ├── scripts/               skill エントリーラッパー + install.sh
        └── assets/                同梱 wheel + サンプル V2 カード
```

> **v0.5.0 注記。** 以前のバージョンではライブラリ管理を別 skill
> `hermes-tavern-cards` として配布していました。v0.5.0 で
> `hermes-tavern` に統合済み —— ユーザーは 1 つの skill だけ
> インストールすれば良く、Hermes も 1 つの trigger 路由で済みます。
> もし `hermes skills list` にまだ `hermes-tavern-cards` が残って
> いれば、`hermes skills uninstall hermes-tavern-cards` で外して
> ください。

`skills/` サブディレクトリは `openai/skills` および `anthropics/skills` で
使われている `path: "skills/"` 規約に揃えてあるので、
`hermes skills tap add imphillip/SoulTavern` だけで追加設定なしに
動きます。各 skill フォルダは標準の `references/` / `scripts/` /
`assets/` レイアウトを使用 —— コンテンツのあるカテゴリだけが配置されます。

## 既知の制限

- **キーワードトリガー型 lorebook injection はサポートしません。**
  すべての entry は always-on としてレンダリングされます。
  これは忠実度を簡潔さで取引するもので、長コンテキストのモデルでは問題
  ありません;サイズが大きい lorebook はゲーティングではなく agent
  駆動の extended-files フローで扱います。
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
- **ポリシー制限の強い agent では、大きなカードのカテゴリ分けが部分的に
  終わることがあります。** カードが 15k 閾値を超えると、HermesTavern は
  ソース素材をディスクに置き、呼び出し側の agent にカテゴリ分けを
  依頼します。ポリシーで制限された agent は一部のカテゴリ
  (たとえば `kinks.md`)の作成を拒否することがあり、その場合該当
  カテゴリは最終的な HERMES.md インデックスに現れません ——
  キャラクター自体は読み込まれますが、agent が残してくれた範囲の
  内容になります。より広い範囲を取りたい場合は、別モデルの agent で
  `source.md` を再処理してから `soultavern finalize` を再実行
  してください。

## 開発

```bash
git clone https://github.com/imphillip/SoulTavern.git && cd SoulTavern
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                    # 全スイートを実行
pytest -k staging         # サブセットを実行
pytest tests/test_real_cards_smoke.py   # リアルカード smoke(カードがなければ自動 skip)
```

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
