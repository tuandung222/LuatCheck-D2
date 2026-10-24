"""Small, dependency-light statistics for the D2 benchmark analysis (numpy only; no src/ imports).

Everything here is a pure function of the numbers it is given. Nothing is imputed: an empty or degenerate input yields
None (never 0.0 or a default), so a missing result stays visible as a placeholder downstream.

Conventions
  * Percentiles use numpy's default linear interpolation. With few trials p95 is close to the maximum; the sample size is
    always reported next to it.
  * Intervals are percentile bootstrap intervals over *tasks* (the independent units). Seeds of one task are averaged
    first, because repeated seeds of the same task are not independent samples of the task population.
  * The bootstrap seed is fixed (BOOTSTRAP_SEED) so the numbers are reproducible from the recorded rows.
"""
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

BOOTSTRAP_SEED = 20261023
BOOTSTRAP_DRAWS = 5000


def percentile(values: Sequence[float], q: float) -> Optional[float]:
    return float(np.percentile(list(values), q)) if len(values) else None


def percentiles(values: Sequence[float], qs: Iterable[float] = (50, 95)) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {f"p{int(q)}": percentile(values, q) for q in qs}
    out["n"] = len(values)
    return out


def mean(values: Sequence[float]) -> Optional[float]:
    return float(np.mean(list(values))) if len(values) else None


def sd(values: Sequence[float]) -> Optional[float]:
    """Sample standard deviation (ddof=1); None below two values."""
    return float(np.std(list(values), ddof=1)) if len(values) > 1 else None


def bootstrap_mean_ci(per_unit: Sequence[float], draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED,
                      level: float = 0.95) -> Optional[Dict[str, Any]]:
    """Mean and percentile bootstrap CI over independent units (e.g. per-task values already averaged over seeds)."""
    data = np.asarray(list(per_unit), dtype=float)
    if len(data) < 2:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(data), size=(draws, len(data)))
    means = data[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
    return {"mean": float(data.mean()), "ci95": [float(lo), float(hi)], "n_units": int(len(data)), "draws": draws}


def paired_bootstrap(a_by_unit: Mapping[Any, float], b_by_unit: Mapping[Any, float], draws: int = BOOTSTRAP_DRAWS,
                     seed: int = BOOTSTRAP_SEED, level: float = 0.95) -> Optional[Dict[str, Any]]:
    """Paired difference b - a over the units present in both mappings (tasks), resampling units.

    Returns the observed mean difference, a percentile CI, a two-sided bootstrap p-value (2 * min tail mass, a
    resampling approximation rather than an exact test) and the share of resamples with b > a / b < a. None when fewer
    than two common units exist.
    """
    common = sorted(set(a_by_unit) & set(b_by_unit), key=str)
    if len(common) < 2:
        return None
    a = np.asarray([a_by_unit[k] for k in common], dtype=float)
    b = np.asarray([b_by_unit[k] for k in common], dtype=float)
    d = b - a
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(draws, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
    below = float((means <= 0).mean())
    above = float((means >= 0).mean())
    return {"n_units": int(len(d)), "mean_a": float(a.mean()), "mean_b": float(b.mean()), "diff_b_minus_a": float(d.mean()),
            "ci95": [float(lo), float(hi)], "p_two_sided_bootstrap": float(min(1.0, 2 * min(below, above))),
            "share_resamples_b_gt_a": float((means > 0).mean()), "share_resamples_b_lt_a": float((means < 0).mean()),
            "units_b_better": int((d > 0).sum()), "units_a_better": int((d < 0).sum()), "units_tied": int((d == 0).sum()),
            "draws": draws}


def wilson_interval(successes: int, n: int, z: float = 1.96) -> Optional[List[float]]:
    """Wilson score interval for a binomial proportion (trial-level rates such as the execution-error rate)."""
    if n <= 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]


# ----------------------------------------------------------------------------- agreement

def percent_agreement(x: Sequence[Any], y: Sequence[Any], weights: Optional[Sequence[float]] = None) -> Optional[float]:
    if len(x) != len(y):
        raise ValueError("label sequences must have equal length")
    if not len(x):
        return None
    w = np.ones(len(x)) if weights is None else np.asarray(weights, dtype=float)
    match = np.asarray([a == b for a, b in zip(x, y)], dtype=float)
    return float((w * match).sum() / w.sum())


def cohen_kappa(x: Sequence[Any], y: Sequence[Any], weights: Optional[Sequence[float]] = None,
                scheme: str = "nominal", order: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
    """Cohen's kappa between two raters over the same items.

    scheme "nominal" (unweighted) or "linear" (linear-weighted kappa for ordered labels, `order` gives the label order).
    `weights` are optional per-item sample weights (e.g. inverse inclusion probabilities of a stratified sample).
    kappa is None when it is undefined (no items, or chance agreement equals 1, e.g. both raters constant).
    """
    if len(x) != len(y):
        raise ValueError("label sequences must have equal length")
    n = len(x)
    out: Dict[str, Any] = {"kappa": None, "n": n, "scheme": scheme, "observed_agreement": None, "chance_agreement": None}
    if n == 0:
        out["reason"] = "no items"
        return out
    labels = list(order) if order is not None else sorted(set(x) | set(y), key=str)
    index = {lab: i for i, lab in enumerate(labels)}
    for value in list(x) + list(y):
        if value not in index:
            raise ValueError(f"label {value!r} is not in the label set {labels}")
    k = len(labels)
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    table = np.zeros((k, k))
    for a, b, wt in zip(x, y, w):
        table[index[a], index[b]] += wt
    table /= table.sum()
    row, col = table.sum(axis=1), table.sum(axis=0)
    if scheme == "linear":
        if k < 2:
            out["reason"] = "fewer than two labels"
            return out
        penalty = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    elif scheme == "nominal":
        penalty = 1.0 - np.eye(k)
    else:
        raise ValueError(f"unknown kappa scheme {scheme!r}")
    observed_disagreement = float((penalty * table).sum())
    expected_disagreement = float((penalty * np.outer(row, col)).sum())
    out["observed_agreement"] = float(np.trace(table))
    out["chance_agreement"] = float(np.trace(np.outer(row, col)))
    if expected_disagreement == 0:
        out["reason"] = "undefined: chance disagreement is zero (a rater used a single label)"
        return out
    out["kappa"] = float(1.0 - observed_disagreement / expected_disagreement)
    return out


def bootstrap_agreement(x: Sequence[Any], y: Sequence[Any], draws: int = 2000, seed: int = BOOTSTRAP_SEED,
                        scheme: str = "nominal", order: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
    """Percentile bootstrap CIs (over items) for percent agreement and kappa; None below 5 items."""
    n = len(x)
    if n < 5:
        return None
    rng = np.random.default_rng(seed)
    xa, ya = list(x), list(y)
    agree, kappas = [], []
    for _ in range(draws):
        pick = rng.integers(0, n, n)
        bx, by = [xa[i] for i in pick], [ya[i] for i in pick]
        agree.append(percent_agreement(bx, by))
        kappa = cohen_kappa(bx, by, scheme=scheme, order=order)["kappa"]
        if kappa is not None:
            kappas.append(kappa)
    return {"agreement_ci95": [float(np.percentile(agree, 2.5)), float(np.percentile(agree, 97.5))],
            "kappa_ci95": ([float(np.percentile(kappas, 2.5)), float(np.percentile(kappas, 97.5))] if len(kappas) > draws * 0.5 else None),
            "kappa_defined_in_resamples": len(kappas), "draws": draws}


def agreement_summary(x: Sequence[Any], y: Sequence[Any], weights: Optional[Sequence[float]] = None,
                      scheme: str = "nominal", order: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
    kappa = cohen_kappa(x, y, scheme=scheme, order=order)
    out = {"n": len(x), "percent_agreement": percent_agreement(x, y), "kappa": kappa["kappa"], "kappa_scheme": scheme,
           "chance_agreement": kappa["chance_agreement"], "kappa_note": kappa.get("reason"),
           "bootstrap": bootstrap_agreement(x, y, scheme=scheme, order=order)}
    if weights is not None:
        out["weighted_percent_agreement"] = percent_agreement(x, y, weights)
        out["weighted_kappa"] = cohen_kappa(x, y, weights=weights, scheme=scheme, order=order)["kappa"]
    return out
