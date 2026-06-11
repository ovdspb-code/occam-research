#!/usr/bin/env python3
"""Duellum Veritatis No.9 — avalanche-criticality false-positive reproduction.

Reproduces the decisive observable of the duel: the false-positive rate (FPR)
of a fully validated avalanche power-law + crackling-relation pipeline on a
matched subcritical (m=0.9) Galton-Watson branching control, alongside the
true-positive rate (TPR) on a critical (m=1.0) positive control, scanned across
literature-typical to large sample sizes.

The pipeline is the FINAL repaired version argued in the duel:
  * discrete (Hurwitz-zeta) MLE of the power-law exponent,
  * KS-minimised lower cutoff x_min (Clauset-style),
  * asymptotic 5% KS threshold 1.36/sqrt(n_tail),
  * crackling relation: log-binned <S>(T) slope vs (alpha-1)/(tau-1), 20% band,
  * an n_aval >= 150 admissibility gate.

A condition PASSES (is called "critical") only if BOTH the power-law and the
crackling tests pass. FPR = pass-rate on the subcritical control; TPR =
pass-rate on the critical positive control. Wilson 95% CIs are reported.

All numbers consumed by the published figures come from the cc_data.json this
script writes. Deterministic: a single fixed master seed.
"""
import json
import numpy as np
from scipy.special import zeta

MASTER_SEED = 20260611
rng = np.random.default_rng(MASTER_SEED)


# ---- generative model: Galton-Watson branching avalanches -----------------
def gw(m, cap=50000):
    """One Galton-Watson avalanche with Poisson offspring mean m.
    Returns (size, duration). Critical at m=1.0; subcritical for m<1."""
    size = 1
    cur = 1
    dur = 1
    while cur > 0:
        cur = rng.poisson(m * cur)
        if cur > 0:
            dur += 1
            size += cur
        if size > cap:
            break
    return size, dur


def sample(m, n):
    S = np.empty(n, dtype=np.int64)
    D = np.empty(n, dtype=np.int64)
    for i in range(n):
        S[i], D[i] = gw(m)
    return S, D


# ---- the validated pipeline -----------------------------------------------
def mle_tau(x, xmin):
    """Discrete power-law MLE via Hurwitz zeta + KS distance at this xmin."""
    x = x[x >= xmin]
    if len(x) < 20:
        return np.nan, np.inf, 0
    grid = np.arange(1.05, 4.01, 0.01)
    nll = grid * np.sum(np.log(x)) + len(x) * np.log(zeta(grid, xmin))
    tau = grid[np.argmin(nll)]
    xs = np.unique(x)
    Fe = np.searchsorted(np.sort(x), xs, side="right") / len(x)
    Ft = 1 - zeta(tau, xs + 1) / zeta(tau, xmin)
    D = np.max(np.abs(Fe - Ft))
    return tau, D, len(x)


def fit_xmin(x, xmins=range(1, 9)):
    """KS-minimising x_min selection (Clauset et al.)."""
    best = (np.nan, np.inf, 0, 1)
    for xm in xmins:
        tau, D, n = mle_tau(x, xm)
        if np.isfinite(tau) and D < best[1]:
            best = (tau, D, n, xm)
    return best  # tau, D, n_tail, xmin


def beta_logbin(S, D, xminD, nb=12):
    """Crackling slope: log-binned <S>(T) regression slope above xminD."""
    sel = D >= xminD
    S = S[sel]
    Df = D[sel].astype(float)
    if len(Df) < 30:
        return np.nan
    edges = np.logspace(np.log10(Df.min()), np.log10(Df.max() + 1), nb)
    Tc = []
    Sc = []
    for i in range(len(edges) - 1):
        m = (Df >= edges[i]) & (Df < edges[i + 1])
        if m.sum() >= 10:
            Tc.append(np.sqrt(edges[i] * edges[i + 1]))
            Sc.append(S[m].mean())
    if len(Tc) < 3:
        return np.nan
    return np.polyfit(np.log(Tc), np.log(Sc), 1)[0]


def pipeline(S, D, nmin=150):
    """Full diagnostic pipeline. Returns dict or None if gated out (n<nmin)."""
    if len(S) < nmin:
        return None
    tau, Ds, ns, xmS = fit_xmin(S)
    alpha, Dd, nd, xmD = fit_xmin(D)
    if not (np.isfinite(tau) and np.isfinite(alpha)):
        return None
    pl_ok = (Ds < 1.36 / np.sqrt(ns)) and (Dd < 1.36 / np.sqrt(nd))
    bf = beta_logbin(S, D, xmD)
    bp = (alpha - 1) / (tau - 1)
    crack_ok = bool(np.isfinite(bf) and abs(bf - bp) / bp < 0.20)
    return {
        "tau": float(tau), "alpha": float(alpha),
        "beta_fit": float(bf) if np.isfinite(bf) else None,
        "beta_pred": float(bp),
        "pl_ok": bool(pl_ok), "crack_ok": crack_ok,
        "pass": bool(pl_ok and crack_ok),
    }


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# ---- the scan --------------------------------------------------------------
N_GRID = [300, 500, 800, 1500, 2500, 4000]
TRIALS = 120

results = []
for n in N_GRID:
    tpr_hits = []  # critical positive control (m=1.0): want PASS=1
    fpr_hits = []  # matched subcritical control (m=0.9): want PASS=0
    for _ in range(TRIALS):
        rc = pipeline(*sample(1.0, n))
        if rc is not None:
            tpr_hits.append(rc["pass"])
        rs = pipeline(*sample(0.9, n))
        if rs is not None:
            fpr_hits.append(rs["pass"])
    k_t, m_t = int(np.sum(tpr_hits)), len(tpr_hits)
    k_f, m_f = int(np.sum(fpr_hits)), len(fpr_hits)
    tpr = k_t / m_t if m_t else float("nan")
    fpr = k_f / m_f if m_f else float("nan")
    lo_t, hi_t = wilson(k_t, m_t)
    lo_f, hi_f = wilson(k_f, m_f)
    row = {
        "n_aval": n,
        "crit_TPR": round(tpr, 4),
        "crit_TPR_ci95": [round(lo_t, 4), round(hi_t, 4)],
        "crit_admitted": m_t,
        "subcrit_FPR": round(fpr, 4),
        "subcrit_FPR_ci95": [round(lo_f, 4), round(hi_f, 4)],
        "subcrit_admitted": m_f,
    }
    results.append(row)
    print(f"n={n:5d}  TPR={tpr:.3f} [{lo_t:.3f},{hi_t:.3f}]  "
          f"FPR={fpr:.3f} [{lo_f:.3f},{hi_f:.3f}]  "
          f"(admitted crit={m_t}/sub={m_f})")

cc = {
    "description": "Duellum Veritatis No.9 — diagnostic FPR/TPR of a validated "
                   "avalanche power-law + crackling pipeline on Galton-Watson "
                   "critical (m=1.0) vs matched subcritical (m=0.9) controls.",
    "master_seed": MASTER_SEED,
    "trials_per_condition": TRIALS,
    "n_aval_gate": 150,
    "rejection_threshold_FPR": 0.20,
    "diagnostic_target_FPR": 0.05,
    "pipeline": "discrete Hurwitz-zeta MLE; KS-minimised x_min over 1..8; "
                "asymptotic KS threshold 1.36/sqrt(n_tail); crackling slope via "
                "log-binned <S>(T) vs (alpha-1)/(tau-1) within 20%; both tests "
                "must pass.",
    "scan": results,
}
with open("2026-06-11_cc_data.json", "w") as f:
    json.dump(cc, f, indent=2)
print("wrote 2026-06-11_cc_data.json")
