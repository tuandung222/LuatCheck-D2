const oneDecimal = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });

/** "2,4 s" for seconds-scale values, "85 ms" below one second. null stays visibly absent. */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return "—";
  if (ms < 1000) return `${integer.format(ms)} ms`;
  return `${oneDecimal.format(ms / 1000)} s`;
}

export function formatCount(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : integer.format(value);
}

export function formatClock(epochSeconds?: number): string {
  if (!epochSeconds) return "";
  return new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit", day: "2-digit", month: "2-digit" }).format(new Date(epochSeconds * 1000));
}

export function shortModelName(name: string | undefined): string {
  if (!name) return "—";
  return name.includes("/") ? name.slice(name.lastIndexOf("/") + 1) : name;
}

export function providerLabel(provider: string | undefined): string {
  if (!provider) return "";
  if (provider === "llamacpp" || provider.startsWith("prism") || provider.startsWith("llama")) return "llama.cpp";
  return provider;
}
