import { Cpu, Database, Layers, ShieldCheck } from "lucide-react";
import { formatCount, providerLabel, shortModelName } from "./format";
import type { Capabilities, Health, ProfileInfo } from "./types";

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

export function ProfileSwitch({ profiles, value, onChange, disabled }: {
  profiles: ProfileInfo[]; value: string | null; onChange: (id: string) => void; disabled: boolean;
}) {
  if (profiles.length <= 1) return profiles[0] ? <span className="profile-static">{profiles[0].short_name || profiles[0].display_name || profiles[0].id}</span> : null;
  return <div className="profile-switch" role="radiogroup" aria-label="Bộ văn bản (corpus)">
    {profiles.map((p) => <button key={p.id} role="radio" aria-checked={p.id === value} disabled={disabled || !p.available} title={p.available ? p.display_name : p.error ?? "Không khả dụng"} className={p.id === value ? "active" : ""} onClick={() => onChange(p.id)}>{p.short_name || p.display_name || p.id}</button>)}
  </div>;
}

export function SystemStrip({ capabilities, health, profile }: { capabilities: Capabilities | null; health: Health | null; profile: ProfileInfo | null }) {
  const model = capabilities?.model;
  const rr = profile?.retrieval?.reranker;
  const ret = profile?.retrieval;
  const stage1 = ret?.mode === "hybrid_index" ? `Hybrid Index (${ret.index?.search_mode || "hybrid"})` : "BM25+TF-IDF";
  const mode = profile?.verifier_mode;
  return <div className="system-strip" aria-label="Hệ thống đang chạy">
    <div className="fact" title={profile?.display_name}><Database size={16} /><span><small>Bộ văn bản</small><b>{profile ? `${formatCount(profile.corpus?.documents)} văn bản · ${formatCount(profile.corpus?.records)} mục` : "—"}</b></span></div>
    <div className="fact" title={model?.endpoint}><Cpu size={16} /><span><small>Model điều khiển (local)</small><b>{shortModelName(model?.name)} <em>{providerLabel(model?.provider)}</em> <Dot state={health?.model.reachable} /></b></span></div>
    <div className="fact" title={rr?.model ?? ret?.index?.path ?? ""}><Layers size={16} /><span><small>Truy xuất</small><b>{rr?.enabled ? <>{stage1} → reranker {rr.top_k_in}→{rr.top_k_out} <Dot state={health?.reranker?.reachable} /></> : profile ? `${stage1} (không rerank)` : "—"}</b></span></div>
    <div className="fact"><ShieldCheck size={16} /><span><small>Kiểm tra mặc định</small><b>{verifierLabel(mode)}</b></span></div>
  </div>;
}
