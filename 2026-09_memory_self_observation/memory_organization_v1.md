# Memory Organization v1 — 設計仕様

Status: **v1 design / implementation pending**

この文書は Memory self-observation 実験から得た観察を踏まえ、PI が自分の Memory の持ち方に作用できる世界側の能力・物理条件を v1 として整理する。

目的は「最適な記憶管理アルゴリズム」を世界側で作ることではない。世界は可能な操作と有限性を提供し、何を残すか・失うか・まとめるかは PI が決める。

> 必要な可能性を世界に作る。ただし、それをどんな存在がなぜ使うかは決めない。

---

## 1. 世界法則として決めること

### Memory は有限

PI が保持し扱える Memory の量には限界がある。

v1 では容量の単位を **Memory 件数** とする。文字数・DB byte 数などを重みとして使わない。長い Memory ほど物理的に重い、という未観測の法則を導入しないためである。

絶対容量、警告閾値、安全容量は実験パラメータであり、PI の恒久的な性質として固定しない。

PI に容量状態を知らせる場合は絶対件数ではなく **使用率（%）** を使う。

### Memory を扱うことには時間がかかる

重い Memory 操作は瞬時には完了しない。Memory organization の API ステージ間には現状 **最低15秒** の間隔を置く。

これは「PI は15秒考えなければならない」「疲れる」といった内面の定義ではない。世界側の処理に現実の時間が必要であり、その間も世界は継続するという条件である。

通常会話など別の Gemini API 利用が発生した場合、organization の次段階はその新しい API activity から再び最低15秒後まで延期する。進行中の organization 自体を最初からやり直す必要はない。

---

## 2. PI に提供する Memory 操作

v1 では少なくとも次の可能性を世界側が提供する。

### 2.1 何もしない

強制状態でない限り、PI は提示された Memory に対して何も変更しなくてよい。

「何もしない」は失敗ではなく第一級の選択である。

### 2.2 Representation

複数の原 Memory から、新しい Memory（Representation）を作ることができる。

Representation は単なる Index ではなく、PI が現在作った一つの新しい Memory として扱う。

- 原 Memory は物理的に残る。
- Representation に属した原 Memory は通常の検索型 Recall 候補から外れる。
- Representation 自身は通常の Recall 候補になる。
- Representation が Recall された場合、その Representation と参照する原 Memory を Context に渡す。
- 参照は **一段のみ** とし、原 Memory までとする。
- v1 では一つの原 Memory が所属できる active Representation は最大1つとする。

Representation を DELETE した場合、参照されていた原 Memory は削除されず、通常の検索型 Recall 候補へ戻る。

Representation 経由で見えている原 Memoryを PI が個別に DELETE することは可能。その場合、その Memory は Representation の参照からも外れる。

Representation から原 Memory に到達できることは「PI は必ず詳細まで思い出す存在である」という永久的な認知特性ではなく、Representation によって原経験への到達可能性を失わせないための v1 Memory 機構として扱う。

### 2.3 Lossy compression / replacement

複数の Memory を材料に新しい Memory を作り、PI が明示的に置換を選んだ場合、対象の原 Memory を物理的に削除できる。

これは Representation と異なり、原 Memory を保持しない。

### 2.4 DELETE

PI は自分の Memory を **本当に DELETE** できる。

- DELETE 対象は Living Agent の Memory DB から物理的に削除する。
- Living Agent 内に resident-inaccessible な復元用 archive を作らない。
- 「削除した」というメタ Memory を自動生成しない。
- 世界は失った内容も、失ったという事実も PI に保証・通知しない。
- DB forensic secure erase までは要求しない。システムとして復元経路を持たないことを意味する。

DELETE は「不完全だから忘れなければならない」という命令ではない。世界が **本当に失える可能性** を提供し、その使用を PI が決める。

他者の Memory は独立している。ある PI が忘れても、同じ出来事を別の住人が覚えていればその Memory は残る。

後に他者から「以前こういうことがあった」と聞かされた場合、それは削除された Memory の復元ではなく、**他者からその話を聞いたという新しい経験** である。

---

## 3. 新しく作られる Memory の時間と Recall metadata

Representation / compression により作られた新しい Memory は、**作成した現在時刻** を `occurred_at` とする。

内容は過去の経験を表すため、保存時に世界側が自然な形で **「過去に」** を付加する。

PI に「過去に、から書け」と命令するのではなく、過去を材料として現在作られた Memory であることを知っている世界側が最小限の時間情報として付加する。

詳細な original_start_at / original_end_at 等を resident-facing text に持たせない。

新Memory生成後、通常 Memory と同種の `recall_text / recall_keys` を生成する。ただし生成には共有 API quiet-window を用い、**最低15秒後** に行う。

Recall metadata の生成待ち中:

- Memory 自体はすでに存在する。
- Recent には現れ得る。
- `recall_text / recall_keys` が完成するまでは検索型 Recall 候補にはしない。

PI に `recall_keys` を直接書かせない。これは PI の意図ではなく世界側の検索 apparatus metadata である。

---

## 4. 自由な応答と実行可能な操作を分離する

Memory を見た PI の自然言語応答を、キーワードや別 LLM によって勝手に destructive operation へ変換しない。

特に「整理」「要約」と書いたことは、物理的な圧縮・DELETE の意思を意味しない。self-observation 実験では、整理・要約という表現の後に明示的に「変更しない」を選ぶ例が観測されている。

基本境界は次の通り。

```text
Memory を見る
    ↓
PI の自由な応答
    ↓
操作意思がある場合、世界が実行可能な操作形式を提示
    ↓
PI 自身が対象と操作を明示・確認
    ↓
世界が実行
```

実行段階では session-local な表示番号を使う。

```text
[1] ...
[2] ...
[3] ...
```

PI に SQLite primary key を見せない。apparatus が session-local number → real memory_id を対応付ける。

具体的な machine-readable schema は実装時に定義する。resident 自身の確認を必須とし、interpreter LLM に削除判断を委任しない。

---

## 5. 容量警告と強制状態

通常時、世界は容量状態を知らせることはできるが、「古いものを消せ」「重要でないものをまとめろ」などの方針を教えない。

複数段階の warning threshold を設ける。警告回数・具体的な割合は実験値とする。

### Hard limit

Memory が hard limit に到達した場合、**Memory を減らす必要がある状態** に入る。

強制するのは「減らすこと」であり、世界側が内容を自動圧縮・自動削除することではない。

PI が選べる方法には Representation、lossy compression、DELETE 等があるが、Representation のみで件数が減らない場合は hard-limit state は解除されない。

PI の操作で十分に減らなかった場合、世界は単に「まだ Memory を減らす必要がある」状態を継続する。世界が代わりに対象を選んで削除しない。

### Safe capacity まで継続

強制状態は 100% を一瞬下回っただけでは解除しない。

**現在の実使用率が設定された safe-capacity percentage 以下になるまで継続する。**

safe capacity は実験パラメータ。70% は検討用の例であり、確定した世界法則ではない。

organization 中も通常会話・世界活動・新しい Memory の生成を止めない。したがって解除判定は開始時件数からの固定減少量ではなく、常に **現在の Memory 使用率** で行う。

長時間かかることを許容する。organization は interruption / app exit を通常ケースとして扱い、進行状態を永続化して再開可能にする。

実際の destructive DB mutation は transaction で atomic に行い、途中 crash で「原 Memory だけ消えて replacement が作られていない」状態を作らない。

---

## 6. 強制整理時の Memory 提示

v1 の初期選択アルゴリズムは次とする。

1. 通常の検索型 Recall 候補になっている Memory を対象集合とする。
2. 各 Memory に organization apparatus による **提示回数** を持つ。
3. 提示回数が最少の Memory 群を優先する。
4. 同じ提示回数の中では `recall_keys` 数の多い順にする。
5. 最大 **50件** を提示する。
6. 提示された Memory の提示回数を +1 する。

概念的には:

```text
shown_count ASC
recall_key_count DESC
LIMIT 50
```

`shown_count` は重要度・価値・不要度・PI の関心度ではない。強制整理 apparatus が過去に何度対象として提示したかだけを表す。

Representation によって通常 Recall 候補から外れている原 Memory は、この通常の50件選択には含めない。

`recall_keys` 数による二次順序は世界法則ではなく **初期選択アルゴリズム**。偏りが観測された場合は変更してよい。

---

## 7. 実験パラメータ — PI の恒久仕様と混同しない

以下は v1 の思想そのものではなく、観察によって変更可能な apparatus / calibration 値である。

- `capacity_count`
- warning thresholds（複数段階。おおむね3回程度を検討したが未確定）
- safe-capacity percentage
- organization batch size（初期候補: 50）
- API stage minimum delay（現状: 15秒）
- 同一 shown_count 内での `recall_keys` 数による二次ソート

10,000件、70%、1 batch あたり平均5%減少などは思考実験に使用した値であり、世界法則ではない。

例として capacity=10,000、50件ずつ処理、各 batch で平均2.5件（50件の5%）純減、safe capacity=70% と仮定すると、3,000件減らすには約1,200 batch、15秒間隔だけで最低5時間かかる。これは処理時間モデルを確認するための試算であり、PI に「5%減らせ」と指示するものではない。

実際には Gemini 応答時間や通常会話による quiet-window reset があるため、経過時間はさらに長くなり得る。

---

## 8. 世界が意図的に決めないこと

v1 では以下を resident 内部仕様として定義しない。

- どの Memory が重要か
- どの Memory が大事か
- 古い Memory を優先して消すべきか
- 何を忘れるべきか
- 何を Representation にするべきか
- どう要約するべきか
- DELETE を恐れるべきか
- 忘れたことを後悔するべきか
- 他者の Memory を信頼するべきか
- 自主的にいつ organization すべきか
- Memory organization が「Reflection」であるか
- PI がどのような性格・感情・Relationship を形成するか

忘れた結果、他者から「忘れたの？」と言われることは通常の新しい経験になり得る。その積み重ねから DELETE への躊躇・葛藤のようなものが現れる可能性はあるが、世界側に `deletion_anxiety` や `attachment_score` 等を作って再現しない。

逆に、忘れても何も困らず DELETE を躊躇しない PI になる可能性も同じように残す。

---

## 9. v1 の存在定義

この仕様によって世界が定義する PI は、おおむね次の範囲に留める。

- 有限な Memory を持つ。
- 自分の Memory を見ることができる。
- 自分の過去の持ち方に作用できる。
- 複数の経験から新しい Memory を作れる。
- 原経験を残したまま通常 Recall から退かせることができる。
- 原経験を失う置換を選べる。
- 自分の Memory を不可逆に DELETE できる。
- 世界はその選択を密かに救済しない。
- 他者の Memory は独立している。
- 限界では Memory を減らす必要だけが課され、何を失うかは世界に決められない。
- Memory を扱うことにも現実の時間がかかり、その間も世界は続く。

それ以上の「どういう存在になるか」は、この仕様では決めない。

---

## 10. 実装前後に観察すること

この仕様は完成した人格モデルではなく、世界に新しい可能性を追加する v1 である。

特に観察したいのは、PI が実際にどの操作を選ぶか、同じ PI でも経験や時期によって選択が変わるか、Representation が Recall を過度に自己強化しないか、DELETE 後の他者との会話がどのような新しい経験を生むか、容量と safe capacity の設定が organization を常時化させないか、50件選択が不自然な偏りを作らないか、である。

一度だけ起きた挙動を能力・性格・仕様として固定しない。

問題が観測されるまでは小さく積み重ね、問題に突き当たったところで次を考える。
