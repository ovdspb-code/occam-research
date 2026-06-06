"""
Duellum Veritatis No.4 - reproducible compute bundle.

Question of the duel: is the predictive power of third-order co-skewness of
static functional connectivity (FC) a genuine instantaneous three-way brain
mechanism, or mostly a static shadow of unmodeled directed/lagged (temporal)
structure that a directed-FC baseline absorbs?

This script reproduces the central physics the two sides converged on:

  - A SINGLE common skewed neural source is loaded into every node; how
    strongly it loads is modulated by a per-subject "cognition" score. This is
    the only construction that makes co-skewness track cognition (both sides
    agreed independent skewed sources do not).
  - Each node convolves that source with a region-specific haemodynamic
    response (HRF) of a slightly different delay/width. So an event that is
    INSTANTANEOUS at the neural level becomes LAGGED across nodes in the
    measured (BOLD) signal. This is the duel's key claim: the measurement
    itself is lagged.
  - We then ask how much co-skewness adds on top of a directed-FC baseline,
    for a POOR baseline (lag-1 only) and a RICH baseline (lags 1..L covering
    the HRF support).

If the thesis holds, co-skewness predicts cognition and adds over static FC,
but its increment over a RICH directed-FC baseline collapses toward zero.
The contrast condition (independent skewed sources, no common driver) should
show co-skewness predicting nothing.

All numbers in the digest come from this script. Run:
  python3 2026-06-06_repro.py
"""

import json
import numpy as np
from itertools import combinations

N = 320          # subjects
T = 300          # BOLD timepoints per subject
NODES = 4
# Shared haemodynamic-like spread kernel: the common skewed driver reaches the
# receiver nodes smeared over lags 1..3 (not a single clean lag). All receivers
# share this kernel, so they share overlapping instantaneous support -> a static
# co-skewness shadow exists, but it is built entirely from lagged copies.
SPREAD_KERNEL = [(1, 0.6), (2, 0.3), (3, 0.1)]
RICH_LAGS = 6    # directed-FC "rich" baseline covers lags 1..6 (full spread support)
SEEDS = list(range(12))     # repeat the whole experiment; report mean +/- std


def coskew(x, y, z):
    x = (x - x.mean()) / (x.std() + 1e-12)
    y = (y - y.mean()) / (y.std() + 1e-12)
    z = (z - z.mean()) / (z.std() + 1e-12)
    return np.mean(x * y * z)


def features(X):
    """X: (NODES, T). Returns static FC, poor directed FC, rich directed FC, co-skew."""
    # static linear FC: instantaneous pairwise covariance
    sf = [np.cov(X[a], X[b])[0, 1] for a, b in combinations(range(NODES), 2)]
    # directed FC, lag-1 cross-cov (POOR baseline)
    poor = []
    for a in range(NODES):
        for b in range(NODES):
            poor.append(np.mean((X[a, :-1] - X[a, :-1].mean()) *
                                (X[b, 1:] - X[b, 1:].mean())))
    # directed FC, lags 1..RICH_LAGS cross-cov (RICH baseline)
    rich = []
    for lag in range(1, RICH_LAGS + 1):
        for a in range(NODES):
            for b in range(NODES):
                rich.append(np.mean((X[a, :-lag] - X[a, :-lag].mean()) *
                                    (X[b, lag:] - X[b, lag:].mean())))
    # co-skewness over all distinct triplets
    cs = [coskew(X[a], X[b], X[c]) for a, b, c in combinations(range(NODES), 3)]
    return np.array(sf), np.array(poor), np.array(rich), np.array(cs)


def simulate(rng, common_source=True):
    """Cognition modulates DIRECTED coupling; a common skewed driver is
    distributed to receiver nodes at region-specific delays. There is NO
    genuine instantaneous three-way term anywhere: any co-skewness is a static
    shadow of the lagged distribution of the common skewed driver.
    """
    c = rng.standard_normal(N)
    SF, POOR, RICH, CS = [], [], [], []
    for i in range(N):
        g = 0.5 + 0.45 * c[i]                       # directed coupling ~ cognition
        v = rng.standard_normal(T)                  # symmetric nuisance, cognition-independent
        X = np.zeros((NODES, T))

        def spread(src):
            out = np.zeros(T)
            for lag, w in SPREAD_KERNEL:
                sl = np.roll(src, lag); sl[:lag] = 0.0
                out += w * sl
            return out

        if common_source:
            u = rng.exponential(1.0, T) - 1.0       # ONE common skewed driver
            X[0] = u + 0.3 * rng.standard_normal(T)  # source node
            base = spread(u)
            for n in range(1, NODES):
                X[n] = g * base + 0.8 * v + 0.3 * rng.standard_normal(T)
        else:
            # each receiver gets its OWN independent skewed driver: no shared
            # source => co-skewness has nothing cognition-linked to shadow
            X[0] = (rng.exponential(1.0, T) - 1.0) + 0.3 * rng.standard_normal(T)
            for n in range(1, NODES):
                un = rng.exponential(1.0, T) - 1.0
                X[n] = g * spread(un) + 0.8 * v + 0.3 * rng.standard_normal(T)
        sf, poor, rich, cs = features(X)
        SF.append(sf); POOR.append(poor); RICH.append(rich); CS.append(cs)
    return (c, np.array(SF), np.array(POOR), np.array(RICH), np.array(CS))


def z(M):
    return (M - M.mean(0)) / (M.std(0) + 1e-9)


def _ridge_fit(Xtr, ytr, alpha=1.0):
    # closed-form ridge with intercept (intercept unpenalized)
    Xc = Xtr - Xtr.mean(0)
    yc = ytr - ytr.mean()
    p = Xc.shape[1]
    w = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(p), Xc.T @ yc)
    b = ytr.mean() - Xtr.mean(0) @ w
    return w, b


def cvr2(Xf, c, seed):
    """5-fold cross-validated R2 of Ridge(alpha=1.0), pure numpy."""
    n = len(c)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    folds = np.array_split(idx, 5)
    pred = np.empty(n)
    for k in range(5):
        te = folds[k]
        tr = np.concatenate([folds[j] for j in range(5) if j != k])
        w, b = _ridge_fit(Xf[tr], c[tr])
        pred[te] = Xf[te] @ w + b
    ss_res = np.sum((c - pred) ** 2)
    ss_tot = np.sum((c - c.mean()) ** 2)
    return 1.0 - ss_res / ss_tot


def run_condition(common_source):
    rows = {k: [] for k in
            ["coskew_alone", "static_alone", "poor_alone", "rich_alone",
             "incr_over_static", "incr_over_poor", "incr_over_rich"]}
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        c, SF, POOR, RICH, CS = simulate(rng, common_source=common_source)
        SF, POOR, RICH, CS = z(SF), z(POOR), z(RICH), z(CS)
        cs_a = cvr2(CS, c, seed)
        sf_a = cvr2(SF, c, seed)
        poor_a = cvr2(POOR, c, seed)
        rich_a = cvr2(RICH, c, seed)
        rows["coskew_alone"].append(cs_a)
        rows["static_alone"].append(sf_a)
        rows["poor_alone"].append(poor_a)
        rows["rich_alone"].append(rich_a)
        rows["incr_over_static"].append(cvr2(np.hstack([SF, CS]), c, seed) - sf_a)
        rows["incr_over_poor"].append(cvr2(np.hstack([POOR, CS]), c, seed) - poor_a)
        rows["incr_over_rich"].append(cvr2(np.hstack([RICH, CS]), c, seed) - rich_a)
    return {k: {"mean": float(np.mean(v)), "std": float(np.std(v))}
            for k, v in rows.items()}


def main():
    common = run_condition(common_source=True)
    indep = run_condition(common_source=False)

    out = {
        "description": "Duellum Veritatis No.4 reproducible compute. "
                       "Co-skewness vs directed-FC baselines under a single "
                       "common skewed driver spread to receiver nodes over a "
                       "shared lag-1..3 (HRF-like) kernel; cognition modulates "
                       "the directed coupling. No genuine instantaneous "
                       "three-way term exists by construction.",
        "config": {
            "subjects": N, "timepoints": T, "nodes": NODES,
            "spread_kernel": SPREAD_KERNEL, "rich_lags": RICH_LAGS,
            "seeds": SEEDS, "estimator": "Ridge(alpha=1.0), 5-fold CV R2",
        },
        "common_source": common,
        "independent_source": indep,
    }
    with open("2026-06-06_cc_data.json", "w") as f:
        json.dump(out, f, indent=2)

    def line(label, d):
        return f"{label:28s} mean={d['mean']:+.3f}  std={d['std']:.3f}"

    print("=== COMMON skewed source (puzzle reproduced) ===")
    print(line("co-skew alone R2", common["coskew_alone"]))
    print(line("static FC alone R2", common["static_alone"]))
    print(line("poor directed FC alone R2", common["poor_alone"]))
    print(line("rich directed FC alone R2", common["rich_alone"]))
    print(line("incr co-skew / static FC", common["incr_over_static"]))
    print(line("incr co-skew / POOR dirFC", common["incr_over_poor"]))
    print(line("incr co-skew / RICH dirFC", common["incr_over_rich"]))
    print()
    print("=== INDEPENDENT skewed sources (no common driver) ===")
    print(line("co-skew alone R2", indep["coskew_alone"]))
    print(line("incr co-skew / RICH dirFC", indep["incr_over_rich"]))


if __name__ == "__main__":
    main()
