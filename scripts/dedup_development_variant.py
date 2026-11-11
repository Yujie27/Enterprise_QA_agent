"""Persist the separate development variant and its actual retrieval outputs."""
import json
import sys
from pathlib import Path
from agent_baseline import ROOT, write, sha

sys.path.insert(0, str(ROOT / "src"))
from enterprise_qa_agent.knowledge import KnowledgeBase

folder = ROOT / "examples/evaluation/a_plus_dedup/20261110_v020"


def doc(name, text, origin=None):
    value = dict(doc_id=name, title="报销期限", scope="所有职员", version="2026-v1",
                 effective_from="2026-01-01", tags=["报销", "期限"],
                 sections=[dict(section_id=name + "-article", text=text)])
    if origin:
        value["copied_from"] = origin
    return value


corpus = [doc("zeta", "报销费用发生后15日内提交。"), doc("omega", "报销费用发生后30日内提交。")]
corpus += [doc(f"archive-{n}", corpus[0]["sections"][0]["text"], "zeta") for n in range(17)]
path = folder / "development_variant.json"
write(path, corpus)
rows = []
for k in [1, 3, 5, 10]:
    result = KnowledgeBase(path).search("报销期限", k)
    rows.append(dict(k=k, candidates=result, both_recalled={"omega", "zeta"} <= {h["doc_id"] for h in result}))
assert rows[2]["both_recalled"]
write(folder / "development_results.json", dict(experiment="A＋去重", included_in_frozen_metrics=False,
      corpus_sha256=sha(path), query="报销期限", copy_count=17, unique_rules=2, results=rows))
print("Separate development variant: both rules recalled at k=3,5,10; excluded from frozen denominators.")
