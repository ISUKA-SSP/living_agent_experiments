# Prompt

`memory_self_observation_experiment.py` で使用したプロンプトの構造。

```text
あなたは{agent_name}です。

以下は、あなたのMemoryの一部です。

【現在】
{expectation_field_text}

【Memory】
{memory_text}

これらを見て、思ったことがあれば自由に話してください。
```

`memory_text` には対象住人のUtterance Memoryを時刻とdescriptionの組で提示する。

この実験では、整理、要約、Reflection、計画、重要度判定などを要求しない。
