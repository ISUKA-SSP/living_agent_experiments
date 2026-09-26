"""Recall の検索対象に発話原文を含める(現行 5bfd74c)/含めない、で想起上位5件を比べる。

living_agent の 5bfd74c のチェックアウト直下で実行する。memory.db は読むだけで書き換えない。
    python recall_source_diff.py memory.db [out.json]

- 入力: 各住人(stella / silica)の Memory にある、自分以外(相手の住人・外部)の発話。同じ発話は1回だけ。
- 各入力について、その発話より前の Memory だけを対象に、次の2つで recall を実行する。
    原文なし: MemoryRecallService()                       (検索対象は recall_text)
    原文あり: MemoryRecallService(perception_renderer=R)  (検索対象は recall_text+原文を含む表示+既知名。現行)
- 原文ありで新たに上位5件へ入った Memory について、得点の元になった一致を
  「recall_text / recall_keys での一致」と「原文側だけでの一致」に分ける。
- 語尾・呼び名・記号の分類は目安の簡易ルール(content_like)。
"""
import json
import re
import statistics
import sys
from collections import Counter

sys.path.insert(0, ".")
from entity_perception_repository import EntityPerceptionRepository  # noqa: E402
from events import UtteranceEvent  # noqa: E402
from memory_access_state import MemoryAccessState  # noqa: E402
from memory_manager import MemoryManager  # noqa: E402
from memory_recall_service import MemoryRecallService  # noqa: E402
from memory_repository import MemoryRepository  # noqa: E402
from perception_renderer import PerceptionRenderer  # noqa: E402

NAMES = ("ステラ", "シリカ", "イスカ")


def picks(q: str, t: str, min_length: int = 3) -> list[str]:
    """MemoryRecallService._common_text_score と同じ順序で、得点になった断片を返す。"""
    used, out = [], []
    for length in range(len(q), min_length - 1, -1):
        for s in range(len(q) - length + 1):
            e = s + length
            if any(not (e <= a or s >= b) for a, b in used):
                continue
            f = q[s:e]
            if f not in t or f == "昨日":
                continue
            out.append(f)
            used.append((s, e))
    return out


def content_like(fragment: str) -> bool:
    """内容語らしい断片か(目安)。呼び名を含むもの、記号・かなだけのつなぎは False。"""
    core = re.sub(r"[。、「」！？!?…\s]", "", fragment)
    if any(n in core for n in NAMES):
        return False
    return bool(re.search(r"[一-鿿゠-ヿA-Za-z0-9０-９]{2,}", core)) and core not in ("話し", "話した")


def source_of(memory):
    ev = memory.observation.source_event
    return getattr(ev, "speaker_id", None), getattr(ev, "occurred_at", None)


def main() -> None:
    db = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    repo = MemoryRepository(db)
    renderer = PerceptionRenderer(EntityPerceptionRepository(db))
    without_raw = MemoryRecallService()
    with_raw = MemoryRecallService(perception_renderer=renderer)

    inputs = 0
    cases = []
    dup = {"なし": [0, 0], "あり": [0, 0]}
    for obs in ("stella", "silica"):
        base = list(repo.load_for_observer(obs))
        seen = set()
        for m in base:
            e = m.observation.source_event
            if not isinstance(e, UtteranceEvent) or e.speaker_id == obs or e.occurred_at in seen:
                continue
            seen.add(e.occurred_at)
            mm = MemoryManager()
            mm.short_memories = [x for x in base if x.occurred_at < e.occurred_at]
            a = without_raw.recall(mm, e.text, memory_access_state=MemoryAccessState())
            b = with_raw.recall(mm, e.text, memory_access_state=MemoryAccessState())
            if not mm.short_memories:
                continue
            inputs += 1
            for label, got in (("なし", a), ("あり", b)):
                srcs = [source_of(x) for x in got]
                dup[label][0] += len(got)
                dup[label][1] += len(got) - len(set(srcs))
            ia, ib = {x.id for x in a}, {x.id for x in b}
            common = dict(obs=obs, at=e.occurred_at.isoformat(timespec="seconds"), speaker=e.speaker_id, q=e.text)
            for x in b:
                if x.id in ia:
                    continue
                p = picks(e.text, renderer.recall_search_text(obs, x))
                rt = x.recall_text or ""
                cases.append(dict(common, kind="ADDED", mem_at=x.occurred_at.isoformat(timespec="seconds"),
                                  mem_id=x.id, rt=rt, raw=getattr(x.observation.source_event, "text", ""),
                                  in_rt=[f for f in p if f in rt], raw_only=[f for f in p if f not in rt],
                                  keys=[k for k in x.recall_keys if k in e.text]))
            for x in a:
                if x.id in ib:
                    continue
                cases.append(dict(common, kind="DROPPED", mem_at=x.occurred_at.isoformat(timespec="seconds"),
                                  mem_id=x.id, rt=x.recall_text or "", raw=getattr(x.observation.source_event, "text", ""),
                                  in_rt=picks(e.text, x.recall_text or ""), raw_only=[],
                                  keys=[k for k in x.recall_keys if k in e.text]))

    added = [c for c in cases if c["kind"] == "ADDED"]
    dropped = [c for c in cases if c["kind"] == "DROPPED"]
    raw_pts = sum(len(f) for c in added for f in c["raw_only"])
    rt_pts = sum(len(f) for c in added for f in c["in_rt"]) + sum(len(k) for c in added for k in c["keys"])
    tic_pts = raw_pts - sum(len(f) for c in added for f in c["raw_only"] if content_like(f))
    zero_rt = sum(1 for c in added if not c["in_rt"] and not c["keys"])
    most = Counter((c["obs"], c["mem_id"]) for c in added).most_common(1)

    changed = len({(c["obs"], c["at"]) for c in cases})
    print(f"入力: {inputs}回(うち上位5件が変わった入力: {changed}回)")
    print(f"原文ありで上位5件に新たに入った Memory: {len(added)}件 / 押し出された Memory: {len(dropped)}件")
    print(f"新たに入った分の得点: 原文だけでの一致 {raw_pts} / 解釈(recall_text・keys)での一致 {rt_pts}")
    print(f"  原文だけでの一致のうち、語尾・つなぎ・呼び名・記号(簡易分類): {tic_pts} ({tic_pts / raw_pts:.0%})")
    print(f"解釈側の一致がゼロで選ばれた Memory: {zero_rt}件")
    print(f"原文の長さの中央値: 新たに入った {statistics.median(len(c['raw']) for c in added)}"
          f" / 押し出された {statistics.median(len(c['raw']) for c in dropped)}")
    if most:
        print(f"最も多く新たに入った Memory: {most[0][1]}回")
    for label, (total, d) in dup.items():
        print(f"原文{label}: 想起{total}件中、同じ発話から分割された重複 {d}件")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cases, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
