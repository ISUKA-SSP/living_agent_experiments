# 2026-09-06 決定事項・観察・修正まとめ

## 位置づけ

2026-09-04（金）夜から 2026-09-06（日）夜にかけて進めた、会話継続・Thought・Memory自己観察・知覚境界・CLI観察環境まわりの決定事項と修正をまとめる。

この期間の実装では、機能追加そのものよりも、

- World が何を提供するのか
- PI が何を自分で判断するのか
- Memory / Recall / Thought / Decision の責任境界

をより明確にすることを重視した。

---

## 現在の設計思想

PI（PerfectlyIncomplete）を外部から過剰に規定しない。

World / infrastructure 側は、

- 知覚の機会
- 応答の機会
- 物理的・実装上の可能条件

を提供する。

一方で、

- 何を考えるか
- 話すか待つか
- 思い出したものを今の出来事に関係あるものとして扱うか
- 会話を続けるか終えるか

は、可能な限り PI 自身の判断に委ねる。

「質問だから返答する」「挨拶だから返す」「同じ話題が続いたから打ち切る」のような外部ルールは、必要性が観察されない限り導入しない。

---

## 1. Thought を PI 自身の生成へ移行

従来の RuleBasedThinkGenerator は、質問・要望・挨拶などをシステム側で解釈し、Thought をほぼ規定していた。

これを見直し、Gemini による PI 自身の Thought 生成へ移行した。

新しい基本フローは次の通り。

```text
Perception
  -> Recall / Expectation / Self State
  -> Thought
  -> Decision
  -> Action
```

Thought は「返答や行動を決める場」ではなく、現在の知覚と自身の状態・経験を受けて生じる考えとして扱う。

### 関連コミット（living_agent）

- `96a75a7a63bfc76ebaabc40dff3fef93f80aa933` Add PI-generated Thought
- `f52ad6fe56147d4f13fb3c35c4f8ae774f12cacd` Use PI-generated Thought in main flow
- `5f3a15b8cbfd1c13361d772550647cbbd4a57da0` Test PI-generated Thought prompt

---

## 2. Recall が Thought に与える影響の観察

Thought を PI 自身に生成させるようになったことで、従来は目立ちにくかった Recall の影響が露出した。

観察された例では、現在の話題と直接関係の薄い過去要素（例：アンディ・クラーク、効率、図書館、分類など）を Thought が積極的に統合し、現在の会話を大きく解釈し直すことがあった。

これは単純な「誤答」というより、

```text
Recall として渡された
  -> 今の状況に関係がある情報なのだろう
  -> Thought 内で統合する
```

という暗黙の意味づけが発生している可能性が高い。

### 現在の考え

Recall は、

**「現在の出来事に関連すると確定した証拠」ではなく、単に浮かんできた過去の経験**

として提示したい。

そのため Thought prompt の見出しを、

```text
【思い出した経験】
```

から、

```text
【ふと思い出した経験】
```

へ変更する小さな実験を行う。

現時点では、まず「ふと」の追加だけに留める。

追加ルールとして「関係がなければ無視せよ」などを強制しない。

狙いは、Recall の関連性判断そのものを PI に返すこと。

---

## 3. 誤解は消すのではなく、自己増幅の扱いを観察する

会話中には以前から時折、誤解や意味の取り違えが見られていた。

これは完全に排除すべきものとは考えない。

今回特に観察されたのは、ある解釈が一度会話に現れると、

```text
PI A の解釈
  -> Utterance
  -> PI B がそれを新しい事実材料として扱う
  -> 次の解釈
  -> 再び Utterance
```

という形で、解釈フレームが自己強化される現象。

例：

- ステラ = 効率・安定
- シリカ = 感覚・変化球
- 二人を外からどう見るかユーザーに評価してほしい

というフレームが、単純な本の話題から長く持続した。

### 決定

- 誤解そのものを禁止しない
- 同じ話題だからという理由だけでシステム側が会話を切らない
- Memory が増えるにつれてループ傾向が弱くなっている観察があるため、現時点では性質として保留
- WAIT で自然収束する場合も、別話題へ遷移する場合もあるため、固定制御は入れない

---

## 4. WAIT は本当に「何も表示しない」

従来 CLI では、PI が WAIT を選ぶと、

```text
ステラは今は何も話さず、様子を見ています。
```

とシステム側が表示していた。

しかしこれは、PI が「話さない」を選んだ直後に、システムが代わりにその沈黙を説明してしまう状態だった。

### 決定

通常表示では WAIT を何も表示しない。

`/debug on` の場合のみ、Decision trace で WAIT を確認できる。

### 関連コミット（living_agent）

- `c4e360b48845c618795be2fc8dbedf4364f9f7a4` Keep WAIT silent in CLI presentation

---

## 5. CLI の `あなた > ステラ >` 表示競合

自動継続が `input("あなた > ")` の待機中に発火すると、同じ行へ住人発言が出力され、

```text
あなた > ステラ > ...
```

のように表示される問題があった。

これは会話世界や Event の問題ではなく、CLI の stdout / input 表示競合。

### 最小修正

自動継続の住人発言を表示する前に、現在の入力プロンプト行を改行して区切る。

結果：

```text
あなた >
ステラ > ...
```

となる。

入力途中の文字列まで完全に退避・復元するには `input()` 自体の置き換えが必要であり、GUI 前提なら過剰なので現時点では行わない。

### 関連コミット（living_agent）

- `e4ab0ac556ed05b10db5def006c89014d5bc4553` Separate automatic continuation from input prompt

---

## 6. Recall debug / MemorySummarizer の表示ノイズ除去

Thought 観察をしやすくするため、通常の Recall score debug と MemorySummarizer raw response の CLI 出力を削除した。

これらは内部挙動・Memory persistence・Recall scoring 自体には影響しない。

### 関連コミット（living_agent）

- `fcbbcc2a5491d89bea5b5d23d202d1c207c6a0fc` Remove noisy recall debug output
- `3916bf0f61d3da99dd6d5e97a8509e05eb9da7f3` Remove MemorySummarizer raw response output

---

## 7. Activity / Attention / PI-specific Perception

この週末までに、PI の現在状態と知覚境界を以下のように整理した。

### Activity と Attention

- activity = PI が何をしているか
- attention = 周囲へどう注意を向けているか

別概念として扱う。

例：

```text
activity = Memoryを見ている
attention = 集中している
```

### Focused perception

集中中の PI は ambient utterance を常に完全知覚するとは限らない。

- direct recipient -> 全文知覚
- 自分の名前が含まれる -> 最後の自分の名前から末尾まで知覚
- 名前なし ambient -> 知覚しない

重要なのは、WorldEvent の全文と PI が実際に受け取った Perception を分離すること。

PI の Thought / Recall query / Memory には、実際に知覚した内容だけを渡す。

---

## 8. Memory 自己観察の durable lifecycle

Memory 自己観察は、PI の一時状態と耐久経験を分離した。

### 一時状態

runtime overlay：

```text
activity = Memoryを見ている
attention = 集中している
```

### durable Memory

- Memory を見始めた
- Memory を見ることを終えた

のみを通常 Memory として残す。

強制終了時は、開始 Memory が残っていても完了 Memory を捏造しない。

また same-resident re-entry guard を追加し、同じ PI の self-observation が active / pending の状態で二重起動しないよう infrastructure 側で保護する。

これは PI の判断制約ではなく、一つのセッション状態を壊さないための実装整合性制約。

---

## 9. 自動会話の現在地

住人同士の自動継続は、

```text
EstablishedTurn
  -> presentation 完了
  -> delay
  -> observer に response opportunity
  -> Thought
  -> Decision(TALK / WAIT)
```

で進む。

ユーザー入力が delay 中に来た場合は、古い continuation を cancel し、ユーザー発話を優先する。

WAIT は正常終了。

また、複数 PI が同一機会で TALK を選んだ場合は、発話生成は独立に行い、最初に成功した TALK のみが World fact になる。

生成失敗は PI の Thought / Decision / Memory として偽装しない。

---

## 10. 今回あえて保留したもの

### 同話題ループ制御

「同じ話題が N 回続いたら停止」などは入れない。

理由：

- Memory が増えるにつれて長いループが減る傾向が見られる
- WAIT で止まることもある
- 別話題へ自然遷移することもある
- その性質自体が PI の会話特性として観察対象になる

### 誤解の排除

誤解は即座にバグ扱いしない。

ただし、誤解が Memory 内で「事実」へ昇格していく問題は将来的に検討する。

### Memory provenance / epistemic status

将来、以下を区別できるとよい可能性がある。

- user が言った
- PI が考えた
- PI が推測した
- 実際に World で起きた

ただし現段階では大きな構造変更は行わない。

### `profile.personality`

Gemini Thought prompt には現在も personality が含まれている。

現在の「PI を外部から縛らない」方向から見ると、過去設計由来の要素である可能性がある。

今すぐ削除せず、まず観察対象とする。

---

## 11. 今日の観察で確認できたこと

- Gemini Thought 化後も WAIT は残っている
- TALK 一辺倒にはなっていない
- 自動会話は長く継続しても自然に WAIT で止まることがある
- Recall の混入問題と、直前会話だけで成立する自己増幅ループは別問題
- 会話ループは完全な破綻ではなく、意味的にはかなり一貫していることもある
- システム側の安易な打ち切りより、性質として観察する価値が高い
- Memory が増えるにつれて振る舞いが変化しているように見える

---

## 今後の優先観察

1. `【ふと思い出した経験】` への変更だけで Recall の過剰統合がどの程度変わるか
2. 誤解・解釈フレームがどの程度自然に薄れる / 修正される / 別話題へ移るか
3. Memory 増加と会話ループ傾向の変化
4. Thought と Decision が役割分離されたまま維持されるか
5. 部分知覚時に canonical event の情報が漏れないか
6. `profile.personality` が Thought にどの程度強く影響しているか

---

## まとめ

今回の進展は、PI に新しいルールを与えたというより、むしろ既存の外部ルールを剥がし、PI 自身が判断できる範囲を増やす方向だった。

その結果として、Recall の影響、誤解、会話の自己増幅、WAIT による自然収束など、以前は見えにくかった性質がより直接観察できるようになった。

現段階では、それらをすぐ矯正するのではなく、

**「世界は機会と条件を提供し、PI がそこからどう振る舞うかを観察する」**

という方針を維持する。
