# Living Agent 現行設計（レビュー用）

対象: この作業環境の `living_agent` ソース。実際の GitHub Draft PR のコミットとの差分は未確認（このコピーの Git 履歴は空）。記載内容はコードで確認できた範囲に限定する。

## 構成と実行順

| 責務 | 主なファイル | 現行の流れ |
| --- | --- | --- |
| 起動と CLI | `main.py` | ステラ、シリカ、LivingRoom、Memory DB、サービスとスケジューラを構築。外部入力と `/pass`、`/observe-memory` などを受ける。 |
| 世界と出来事 | `world.py`, `events.py` | `WorldState` が住人とイベントアーカイブを保持。`UtteranceEvent` は客観的な `speaker_id` と発話、宛先、元の位置、到達先を持つ。 |
| 知覚と反応 | `event_dispatcher.py`, `utterance_perception.py`, `observation_policy.py`, `response_policy.py` | 観測できる住人に応答機会を渡し、Context → Thought → Decision → Action を生成して成立したイベントを保存する。 |
| 文脈と生成 | `context_builder.py`, `prompt_builder.py`, `gemini_think_generator.py`, `rule_based_decision_generator.py`, `response_generator.py` | 直近・Recall・予測などの材料とプロフィールから、各住人の思考、判断、発話を組み立てる。生成は `GeminiTextGenerator` を利用する。 |
| Memory | `memory_recorder.py`, `observation_factory.py`, `memory_repository.py`, `memory_recall_service.py` | 観測者ごとの Observation/Memory を SQLite に保存し、Recall に使用。Memory の元イベント ID を保つ。 |
| 他者認知 | `entity_perception_repository.py`, `perception_renderer.py`, `explicit_self_introduction_name_extractor.py` | `observer_id` ごとの既知名を保持。明示的な名乗りを知覚した住人だけに反映し、過去の元イベントは更新せず表示時に現在の認知を使う。 |
| 時間経過 | `conversation_continuation_scheduler.py`, `memory_capacity_scheduler.py` | 45 秒後の会話機会と Memory 容量観測を実行。CLI 入力と実行ロックを共有する。 |

## 外部接続と位置

- 外部入力は `speaker_id=external_001`, `location_id=None`, `delivery_location_id=living_room`。外部存在本人は住人一覧へ追加しない。外部発話の到達先だけを LivingRoom として扱う。
- ステラとシリカは初期状態で `location_id=living_room`。住人の発話は各自の位置から届く。
- 名前は ID に焼き込まず observer ごとの `known_name` として保存する。古いイベントの表示は認知に応じて変わり得る。
- `observable_location_id` は到達先を優先し、旧イベントでは `location_id` を使用する。

## 今回追加した API 保護と表示

- `GeminiTextGenerator.generate` と `generate_json` の送信直前に、全インスタンスで共有する移動窓の上限を適用する。10 秒間で20回を許可し、21回目は API に送らず例外にする。時刻判定は単調増加時計で、複数スレッドからの取得をロックで保護する。
- 上限に達した処理と API 失敗は、CLI では `[システム]` で表示する。自動継続処理は停止し、CLI からの入力は次の入力を受け付ける。エラーを住人の発話や Thought として記録しない。
- 上限は**プロセス内の Gemini 文章生成器**に対するもので、別プロセスの合算、Embedding、実験用スクリプト、時間単位の上限、円建て課金額の制御は対象外。プロセス再起動で窓はリセットされる。
- API エラーの自動再試行は追加していない。追加の API 呼び出しを誘発せず、失敗を表示して止める。`ApiActivityStore` は従来通り最終送信時刻を保存する。

## レビュー時の確認点

1. 外部入力を知覚した住人だけが応答・名乗りの記憶を得ているか。
2. 複数人への入力で20回／10秒の境界が通常操作を妨げないか。
3. 生成途中の API エラーでは、イベントアーカイブと Memory 保存の間に部分的な進行が起こり得る。回復方針が必要か実運用で確認する。
4. 実際の API 利用料と呼び出し数を計測し、将来の時間単位の停止条件を決める。

## 検証条件

この環境では `pytest` が未導入。Python 構文検査および並行20呼び出し後の21回目拒否を実行済み。`test_api_request_limiter.py` に回帰テストを追加したが、テストスイート全体は実行できていない。
