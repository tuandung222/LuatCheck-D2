import json,sys,time,statistics as st
sys.path.insert(0,".")
from src.retrieval.rerankers import CrossEncoderReranker
alias=sys.argv[1]
cands=json.load(open("evaluation/runs/reranker-parity-2026-10-23/candidates.json"))
corp={r["doc_id"]:r for r in json.load(open("data/corpus/hcmut_academic_v1.json"))}
rr=CrossEncoderReranker("AITeamVN/Vietnamese_Reranker",device="mps",dtype="float16",local_files_only=True)
ents=cands["benchmarks"]["hcmut_v1"]["entries"][:12]
def docs(e): return [{"title":corp[c["doc_id"]]["title"],"content":corp[c["doc_id"]]["content"]} for c in e["candidates"]]
rr.score(ents[0]["query"],docs(ents[0]))
w=[]
out=[]
for e in ents[2:12]:
    s=rr.score(e["query"],docs(e)); w.append(rr.last_run["wall_ms"]); out.append(s)
print(alias,"p50 ms/query",round(st.median(w)),"mean",round(st.mean(w)))
json.dump(out,open(sys.argv[2],"w"))
