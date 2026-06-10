#!/usr/bin/env python3
"""Duellum Veritatis No.7 reproduction.

Candidate hypothesis (PRO/loser): in a biologically realistic sparse regime the
coskewness-driven leakage dominates asymptotically, so the *explained entropy*
of a pairwise MaxEnt model (S1-S2) converges, as p->0, to a quantity set
entirely by higher-order coskewness, making it asymptotically uninformative
about mechanism.

This script reproduces the two pieces of evidence that decided the duel:

  TEST A (decisive, definitional).  Hold the first moments (means) and the
  second moments (pairwise correlations) of a 3-spin binary distribution fixed
  and sweep the third moment / coskewness over a wide range, including a sign
  change.  The pairwise MaxEnt fit matches only first and second moments, so
  S1-S2 is a function of those moments alone and must be invariant to the third
  moment.  We verify it numerically: explained entropy is constant to machine
  precision while the *true* entropy S_N (and thus the unexplained residual
  S2-S_N where coskewness actually lives) moves.

  TEST B (falsifier family).  A dichotomized-Gaussian sparse ensemble with a
  fixed equicorrelated latent (the standard Macke et al. spike model).  As the
  threshold pushes the mean activity p toward zero, the higher-order fraction
  HOF = 1 - capt = (S2 - S_N)/(S1 - S_N) stays bounded well below 1 instead of
  rising to 1 -- exactly the falsifier the thesis itself requested.

Deterministic: exact 2^N state enumeration and convex MaxEnt fits; no RNG.
"""

import json
import numpy as np
from itertools import product, combinations
from scipy.optimize import minimize
from scipy.stats import norm, multivariate_normal

LOG2 = np.log(2.0)


def entropy_bits(p):
    p = np.asarray(p, float)
    p = p[p > 1e-300]
    return float(-np.sum(p * np.log(p)) / LOG2)


def all_states(N):
    return np.array(list(product([0, 1], repeat=N)), dtype=float)


# ---------------------------------------------------------------------------
# Pairwise / independent MaxEnt fits by exact enumeration (convex dual).
# ---------------------------------------------------------------------------
def maxent_fit(N, target_means, target_pairs, pairwise=True):
    """Fit a MaxEnt distribution over 2^N binary states.

    pairwise=True matches means E[x_i] and pairwise E[x_i x_j].
    pairwise=False matches means only (independent model).
    Returns (probs, entropy_bits).
    """
    S = all_states(N)
    pair_idx = list(combinations(range(N), 2))
    # feature matrix: columns = [x_i ...] (+ [x_i x_j ...] if pairwise)
    feats = [S[:, i] for i in range(N)]
    targets = [target_means[i] for i in range(N)]
    if pairwise:
        for (i, j) in pair_idx:
            feats.append(S[:, i] * S[:, j])
            targets.append(target_pairs[i, j])
    F = np.array(feats).T               # (2^N, K)
    mu = np.array(targets)              # (K,)

    def obj(theta):
        e = F @ theta
        m = e.max()
        w = np.exp(e - m)
        Z = w.sum()
        logZ = m + np.log(Z)
        model_mu = (F * (w / Z)[:, None]).sum(axis=0)
        val = logZ - theta @ mu
        return float(val), (model_mu - mu)

    theta0 = np.zeros(F.shape[1])
    res = minimize(obj, theta0, jac=True, method="L-BFGS-B",
                   options={"maxiter": 5000, "ftol": 1e-15, "gtol": 1e-12})
    theta = res.x
    e = F @ theta
    e -= e.max()
    w = np.exp(e)
    probs = w / w.sum()
    return probs, entropy_bits(probs)


# ---------------------------------------------------------------------------
# TEST A -- decisive definitional check.
# ---------------------------------------------------------------------------
def joint_from_moments(m, Q, t):
    """Unique 3-spin joint matching means m (3), pairwise Q[i,j] (E[xi xj]),
    and triple moment t = E[x1 x2 x3].  8 states, 8 linear constraints."""
    S = all_states(3)
    rows = [np.ones(8)]
    b = [1.0]
    for i in range(3):
        rows.append(S[:, i]); b.append(m[i])
    for (i, j) in combinations(range(3), 2):
        rows.append(S[:, i] * S[:, j]); b.append(Q[i, j])
    rows.append(S[:, 0] * S[:, 1] * S[:, 2]); b.append(t)
    A = np.array(rows)
    p = np.linalg.solve(A, np.array(b))
    return p, S


def test_A():
    # fixed first and second moments (mean activity p0, equfor pairwise corr)
    p0 = 0.18
    m = np.array([p0, p0, p0])
    # choose a valid pairwise second moment via a small positive correlation
    rho = 0.20
    cov = rho * np.sqrt(p0 * (1 - p0)) * np.sqrt(p0 * (1 - p0))
    q = p0 * p0 + cov               # E[xi xj]
    Q = np.full((3, 3), q)
    # feasible range for triple moment t given fixed m, Q: probabilities >= 0.
    # sweep t across the widest feasible window, including the sign-change of
    # the connected coskewness c3 = E[xyz] - (mixed lower-order terms).
    # find feasible t bounds by scanning.
    ts = np.linspace(0.0, p0, 400)
    feas = []
    for t in ts:
        p, S = joint_from_moments(m, Q, t)
        if (p > -1e-12).all():
            feas.append(t)
    tlo, thi = min(feas), max(feas)
    grid = np.linspace(tlo + 1e-6, thi - 1e-6, 41)

    explained, true_H, S1v, S2v, c3v = [], [], [], [], []
    for t in grid:
        p, S = joint_from_moments(m, Q, t)
        SN = entropy_bits(p)
        _, S1 = maxent_fit(3, m, Q, pairwise=False)
        _, S2 = maxent_fit(3, m, Q, pairwise=True)
        # connected third cumulant (coskewness) of the centred variables
        c = S - m
        c3 = float(np.sum(p * c[:, 0] * c[:, 1] * c[:, 2]))
        explained.append(S1 - S2)
        true_H.append(SN)
        S1v.append(S1); S2v.append(S2); c3v.append(c3)

    explained = np.array(explained)
    return {
        "p0_mean_activity": p0,
        "pairwise_corr_rho": rho,
        "triple_moment_grid_min": float(grid.min()),
        "triple_moment_grid_max": float(grid.max()),
        "coskewness_c3_min": float(min(c3v)),
        "coskewness_c3_max": float(max(c3v)),
        "coskewness_sign_change": bool(min(c3v) < 0 < max(c3v)),
        "coskewness_fold_range": float(max(c3v) / min([x for x in c3v if abs(x) > 1e-9], key=abs)) if any(abs(x) > 1e-9 for x in c3v) else None,
        "explained_entropy_mean_bits": float(explained.mean()),
        "explained_entropy_max_abs_deviation_bits": float(np.max(np.abs(explained - explained.mean()))),
        "true_entropy_min_bits": float(min(true_H)),
        "true_entropy_max_bits": float(max(true_H)),
        "true_entropy_swing_bits": float(max(true_H) - min(true_H)),
        "unexplained_residual_S2_minus_SN_min_bits": float(min(np.array(S2v) - np.array(true_H))),
        "unexplained_residual_S2_minus_SN_max_bits": float(max(np.array(S2v) - np.array(true_H))),
        "n_grid_points": int(len(grid)),
    }


# ---------------------------------------------------------------------------
# TEST B -- dichotomized-Gaussian falsifier family.
# ---------------------------------------------------------------------------
def dg_probs(N, t, rho):
    """Exact state probabilities of an equicorrelated dichotomized Gaussian:
    x_i = 1 iff latent g_i > t, Corr(g_i,g_j)=rho.  Inclusion-exclusion over
    orthant probabilities."""
    Sig = (1 - rho) * np.eye(N) + rho * np.ones((N, N))
    S = all_states(N)
    BIG = 8.5
    out = []
    for s in S:
        ones = [i for i in range(N) if s[i] == 1]
        zeros = [i for i in range(N) if s[i] == 0]
        tot = 0.0
        for r in range(len(ones) + 1):
            for T in combinations(ones, r):
                upper = np.array([t if (i in zeros or i in T) else BIG
                                  for i in range(N)], float)
                tot += ((-1) ** r) * multivariate_normal.cdf(
                    upper, mean=np.zeros(N), cov=Sig, allow_singular=True)
        out.append(max(tot, 0.0))
    p = np.array(out)
    return p / p.sum(), S


def test_B():
    N = 5
    rho = 0.30
    rows = []
    for p_target in [0.30, 0.15, 0.08, 0.04, 0.02, 0.01, 0.005]:
        t = norm.ppf(1 - p_target)
        p, S = dg_probs(N, t, rho)
        m = (S * p[:, None]).sum(axis=0)
        Q = np.zeros((N, N))
        for i in range(N):
            for j in range(N):
                Q[i, j] = float(np.sum(p * S[:, i] * S[:, j]))
        SN = entropy_bits(p)
        _, S1 = maxent_fit(N, m, Q, pairwise=False)
        _, S2 = maxent_fit(N, m, Q, pairwise=True)
        multi_info = S1 - SN                      # total multi-information
        capt = (S1 - S2) / multi_info if multi_info > 1e-9 else float("nan")
        hof = 1.0 - capt
        rows.append({
            "p_obs": float(m.mean()),
            "p_target": p_target,
            "captured_by_pairwise": float(capt),
            "higher_order_fraction": float(hof),
            "multi_information_bits": float(multi_info),
        })
    capts = [r["captured_by_pairwise"] for r in rows]
    hofs = [r["higher_order_fraction"] for r in rows]
    return {
        "N": N,
        "latent_corr_rho": rho,
        "rows": rows,
        "capt_min": float(min(capts)),
        "capt_max": float(max(capts)),
        "hof_max": float(max(hofs)),
        "hof_approaches_one": bool(max(hofs) > 0.9),
    }


def main():
    A = test_A()
    B = test_B()
    data = {
        "duel": "Duellum Veritatis No.7",
        "date": "2026-06-09",
        "test_A_definitional_invariance": A,
        "test_B_dg_falsifier_family": B,
        "headline": {
            "explained_entropy_max_abs_deviation_bits": A["explained_entropy_max_abs_deviation_bits"],
            "true_entropy_swing_bits": A["true_entropy_swing_bits"],
            "coskewness_sign_change": A["coskewness_sign_change"],
            "dg_higher_order_fraction_max": B["hof_max"],
            "dg_capt_range": [B["capt_min"], B["capt_max"]],
            "dg_hof_approaches_one": B["hof_approaches_one"],
        },
    }
    with open("2026-06-09_cc_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print(json.dumps(data["headline"], indent=2))


if __name__ == "__main__":
    main()
