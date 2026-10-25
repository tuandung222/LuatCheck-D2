import { Cpu, Database, Layers, ShieldCheck } from "lucide-react";
import { formatCount, providerLabel, shortModelName } from "./format";
import type { Capabilities, Health, ProfileInfo, RetrievalMode } from "./types";

function Dot({ state }: { state: boolean | null | undefined }) {
  const cls = state === true ? "ok" : state === false ? "bad" : "unknown";
  const label = state === true ? "kết nối được" : state === false ? "không kết nối được" : "chưa rõ";
  return <i className={`dot ${cls}`} role="img" aria-label={label} title={label} />;
}

function verifierLabel(mode?: string) {
  if (!mode) return "—";
  if (mode === "off") return "OFF";
  if (["l1", "lexical", "lexical_grounding", "grounding"].includes(mode)) return "L1 (lexical)";
  return mode;
}

export function retrievalStageLabel(mode?: RetrievalMode | null, profile?: ProfileInfo | null) {
  const effective = mode ?? profile?.retrieval?.active_mode;
  switch (effective) {
    case "hybrid_wrrf":
      return "Weighted RRF 768-d (0.75/0.25)";
    case "bm25_tfidf":
      return "BM25 + TF-IDF";
    case "fts5_keyword":
      return "SQLite FTS5 (BM25)";
    case "vector_768d":
      return "Vector 768-d (Gemma-2)";
    case "hybrid_rrf_equal":
      return "Standard RRF 768-d (50/50)";
    default: {
      const ret = profile?.retrieval;
      return ret?.mode === "hybrid_index" ? `Hybrid Index (${ret.index?.search_mode || "hybrid"})` : "BM25+TF-IDF";
    }
  }
}

export function ProfileSwitch({ profiles, value, onChange, disabled }: {
  profiles: ProfileInfo[]; value: string | null; onChange: (id: string) => void; disabled: boolean;
}) {
  if (profiles.length <= 1) return profiles[0] ? <span className="profile-static">{profiles[0].short_name || profiles[0].display_name || profiles[0].id}</span> : null;
  return <div className="profile-switch" role="radiogroup" aria-label="Bộ văn bản (corpus)">
    {profiles.map((p) => <button key={p.id} role="radio" aria-checked={p.id === value} disabled={disabled || !p.available} title={p.available ? p.display_name : p.error ?? "Không khả dụng"} className={p.id === value ? "active" : ""} onClick={() => onChange(p.id)}>{p.short_name || p.display_name || p.id}</button>)}
  </div>;
}

export function SystemStrip({ capabilities, health, profile, retrievalMode }: {
  capabilities: Capabilities | null;
  health: Health | null;
  profile: ProfileInfo | null;
  retrievalMode?: RetrievalMode | null;
}) {
  const model = capabilities?.model;
  const rr = profile?.retrieval?.reranker;
  const ret = profile?.retrieval;
  const stage1 = retrievalStageLabel(retrievalMode, profile);
  const mode = profile?.verifier_mode;
  return <div className="system-strip" aria-label="Hệ thống đang chạy">
    <div className="fact" title={profile?.display_name}><Database size={16} /><span><small>Bộ văn bản</small><b>{profile ? `${formatCount(profile.corpus?.documents)} văn bản · ${formatCount(profile.corpus?.records)} mục` : "—"}</b></span></div>
    <div className="fact" title={model?.endpoint}><Cpu size={16} /><span><small>Model điều khiển (local)</small><b>{shortModelName(model?.name)} <em>{providerLabel(model?.provider)}</em> <Dot state={health?.model.reachable} /></b></span></div>
    <div className="fact" title={rr?.model ?? ret?.index?.path ?? ""}><Layers size={16} /><span><small>Truy xuất</small><b>{rr?.enabled ? <>{stage1} → reranker {rr.top_k_in}→{rr.top_k_out} <Dot state={health?.reranker?.reachable} /></> : profile ? `${stage1} (không rerank)` : "—"}</b></span></div>
    <div className="fact"><ShieldCheck size={16} /><span><small>Kiểm tra mặc định</small><b>{verifierLabel(mode)}</b></span></div>
  </div>;
}
