#!/usr/bin/env bash
set -u
cd /Users/admin/Desktop/Recents/LuatCheck-D2
RUN=evaluation/runs/reranker-parity-2026-10-23
SC=/private/tmp/claude-501/-Users-admin-Desktop-Recents-LuatCheck-D2/3584b6c4-97bd-4d37-8025-11864587c887/scratchpad
for Q in f32 f16 Q8_0; do
  pkill -f "Vietnamese_Reranker-.*gguf" ; sleep 2
  scripts/reranker/serve_mac.sh $Q > $SC/serve_$Q.log 2>&1 &
  until curl -sf localhost:8082/v1/models >/dev/null; do sleep 1; done
  L=$(echo $Q | tr 'A-Z' 'a-z')
  for POL in chunk nochunk; do
    CC=1500; [ $POL = nochunk ] && CC=0
    [ -f $RUN/scores_gguf_${L}_$POL.json ] || .venv/bin/python evaluation/probes/reranker_parity.py score --out $RUN --label gguf_${L}_$POL --backend llama_cpp --endpoint http://127.0.0.1:8082 --model Vietnamese_Reranker-$Q --server-port 8082 --model-file $HOME/models/reranker/gguf/Vietnamese_Reranker-$Q.gguf --chunk-chars $CC > $SC/score_${L}_$POL.log 2>&1 || echo "FAILED $Q $POL" >> $SC/gguf_failures.log
  done
  .venv/bin/python evaluation/probes/reranker_parity.py tokcheck --out $RUN --label $L --hf-model AITeamVN/Vietnamese_Reranker --model Vietnamese_Reranker-$Q --tasks 10 > $SC/tokcheck_$L.log 2>&1 || echo "tokcheck nonzero $Q" >> $SC/gguf_failures.log
done
echo ALLDONE > $SC/gguf_done.flag
