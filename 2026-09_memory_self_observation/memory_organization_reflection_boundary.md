# Memory Organization — Reflection / Representation 境界整理

Status: **design decision / implementation pending**

この文書は `memory_organization_v1.md` を置き換えるものではなく、その後の議論で確定した **Memory Organization と Reflection、Representation の世界上の位置づけ**を追記として整理する。

---

## 1. Memory Organization の位置づけ

Memory Organization は単なる DB 整理機能ではない。

世界は PI に対して、自分が持つ Memory の一部、Memory が有限であるという物理的事実、現在の Memory に関する状態、Memory へ作用できる可能性を提示する。

その後に何を考え、何をするかは PI が決める。

世界側は最初から `ORGANIZE / PLAN / REFLECT / NONE` のような認知カテゴリへ PI の自由応答を分類しない。整理、予定、感想、Reflection、何もしない、といった言葉は現時点では観察者側の記述語彙である。

実際の物理操作が必要になった場合だけ、後段で実行可能な操作として構造化する。

---

## 2. Reflection は先に機能として定義しない

Memory を PI 自身の対象として渡した結果、PI が過去について考えたり、整理したり、予定を立てたりする一連の営みを、観察者側から Reflection と呼ぶことはできる。

しかし `ReflectionGenerator` や `ReflectionMode` を先に作り、「PI は Reflection する存在である」と内部仕様として定義しない。

順序は次のようにする。

```text
PI に自分の過去が渡される
    ↓
PI が自由に反応する
    ↓
結果として過去について考えることがある
    ↓
観察者から見れば Reflection と呼べる
```

Reflection は世界が PI に要求する固定処理ではなく、結果として観察され得る現象として扱う。

---

## 3. 世界の制約と PI の行為を分離する

世界は物理条件を強制できる。

Memory の hard limit などにより「Memory を減らす必要がある」という状態を PI の意思とは無関係に発生させることはできる。

ただし世界は、どの Memory を消すか、Representation するか、どのように解釈するか、Plan を作るかまでは決めない。

**制約は強制されても、それへの認知的対応までは強制されない。**

世界の制約から PI が「あとでこれをしよう」「まずこれを確認しよう」と考えた場合、結果として Plan らしきものが生まれることはある。しかし世界が Plan を生成させたとは扱わない。

Plan を保持できないことが実際の問題として観察された場合に初めて、世界に予定を保持できる可能性が必要かを検討する。現時点では Plan 機構を実装しない。

---

## 4. Representation は世界視点を採用する

Representation の成立には二つの見方がある。

- PI 視点: 過去の複数 Memory から、現在の PI が新しい Memory を成立させた。
- 世界視点: Memory Organization の条件の中で PI が Representation を実行し、その結果が現在の出来事として成立した。

Living Agent v1 では **世界視点**を採用する。

理由は、Memory Organization が Memory の有限性という世界側の物理制約から始まる処理に属するためである。ただし Representation の内容や対象を世界が決めるわけではない。指示・制約は世界から来ても、実行するのは PI である。

Representation Memory だけを DB に特殊経路で直書きせず、既存の世界の文法である

```text
WorldEvent → Observation → MemoryEntry
```

を維持する。

---

## 5. MemoryRepresentationEvent

Representation が成立したとき、新しい `MemoryRepresentationEvent` が発生する。

これは性質として `ThoughtEvent` と同様の **本人内部の Event** として扱う。

- 世界上では実際に起きた Event である。
- 実行した本人だけが Observation できる。
- 他の resident は直接 Observation できない。
- 同じ場所にいることだけを理由に他者へ伝播しない。

したがって、世界で起きた事実であることと、世界にいる全員から観測可能であることを分離する。

現時点の最小形の候補は次の程度とする。

```python
@dataclass(frozen=True)
class MemoryRepresentationEvent:
    agent_id: str
    text: str
    occurred_at: datetime
```

`text` は世界が生成する文章ではなく、PI 自身が生成した Representation 本文である。世界は PI の内容を決めず、PI によって成立した内容を Event として保持する。

Event には source Memory IDs、importance、Representation 理由、compression level、organization state、shown_count、recall_keys 等を入れない。

source Memory との物理的関係は `memory_representation_members` が担当する。

---

## 6. Representation Memory の成立

基本経路は次のようにする。

```text
PI が Representation 本文を成立させる
    ↓
MemoryRepresentationEvent
    ↓
本人だけが Observation
    ↓
ObservationFactory
    ↓
Representation Memory
```

過去の経験を表す Memory であるため、世界側が行う resident-facing text の意味的加工は原則として最小限の **「過去に」** の付加とする。

PI が作った Representation 内容を世界側で要約・評価・解釈し直さない。

`occurred_at` は Representation が成立した現在時刻とする。

Representation の source IDs は relation table に保持し、Event の本文とは分離する。

---

## 7. Organization 中の resident-visible self-state

Memory Organization Session が未完了である間、本人が理解できる現在状態は次の二つに限定する。

1. **自分はいま Memory を整理／扱っている途中である。**
2. **その開始から実時間でどれくらい経過したか。**

経過時間は `started_at` からの wall-clock elapsed time とし、途中で通常会話をしていた時間も含む。

世界は「中断された」「時間がかかりすぎている」「疲れている」「集中している」「処理が重い」といった解釈を付加しない。

API wait、内部 stage、metadata generation 状態、API call 回数など apparatus が知っている低レベル情報も resident-visible にしない。

**apparatus state と resident-visible self-state は同一ではない。**

この状態は自動的に Memory にしない。

---

## 8. Organization State と Representation Event は別物

Organization は時間幅を持つ状態であり、Representation はある時点で成立する Event である。

```text
Organization Session
────────────────────────────
      整理中
      ↑                  ↓
   started_at    MemoryRepresentationEvent
```

両者を一つの概念にまとめない。

---

## 9. Event の発生と永久保存は別

`MemoryRepresentationEvent` が世界で発生したことは、その Event を独立した永久 Event Log として保存し続けなければならないことを意味しない。

Representation Memory が後に物理 DELETE され、その Memory だけが保持していた source Event 情報も失われるなら、それを許容する。

**過去に本当に起きたことと、現在その記録が世界に残っていることは別である。**

これは Memory DELETE の方針とも一致する。

---

## 10. Organization 所要時間の履歴は保留

将来的には、過去の Organization の start / end / duration を世界側で記録し、多数の履歴を何らかの形で圧縮して PI に経験的な時間傾向として渡す可能性を残す。

ただしこれは現在の scope ではない。

世界は「今回あと何分かかる」と予測せず、過去の実際の経験についての情報だけを提供する。平均、中央値、範囲など具体的な圧縮表現もまだ決めない。

履歴が大量になった場合、世界側で圧縮し古い詳細を削除することも候補とする。

---

## 11. 将来への開口部

現在 `MemoryRepresentationEvent` は Memory Organization から利用するが、**Organization からしか発生できない Event とは定義しない。**

将来、PI が別の自然な経路から自分の Memory を Representation する現象が観察された場合、その可能性を閉じないためである。

同様に、Representation のために成立した

```text
PI が自分自身へ作用する
    ↓
内部 Event が成立する
    ↓
本人だけが Observation する
    ↓
Memory になる
```

という経路が、将来 Reflection など別の現象の足掛かりになる可能性はある。

ただし、その可能性を理由に現時点で一般化・抽象化しない。別の実例が同じ構造を必要とした時点で検討する。

---

## 12. 現時点で決めないこと

以下は保留する。

- Reflection を正式な機能にするか
- Plan を正式な機能にするか
- Plan の永続化方法
- Organization 時間履歴の具体形式
- 時間履歴の圧縮方式
- GUI image との連動
- Representation 以外の内部自己作用 Event
- Representation から Representation を作れるか
- Organization 以外から Representation を実行する具体経路
- Reflection / Plan / 感想などを分類する classifier
- PI の心理状態推定

---

## 13. 要約

> 世界は PI に自分の過去と、その過去へ作用できる可能性を与える。世界の物理的制約は PI に要求を課すことがあるが、それに対して何を考え、何を行うかは PI が決める。その結果として生じた内部の行為も、本人だけが観測できる世界上の Event として成立し得る。

Memory Organization はその最初の具体例である。

これは Reflection や Plan を実装することではない。それらが PI から実際に現れたとき、存在できる世界上の入口を作る。
