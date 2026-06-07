#!/usr/bin/env python3
"""Duellum Veritatis No.5 reproducible compute.

Frozen claim (PRO, Athos): the power-law decay exponent alpha of the covariance
eigenspectrum of neural representations is a monotone, computable function of the
network's maximal Lyapunov exponent lambda_max; cortical alpha~1 corresponds to a
specific lambda_max>0 (soft supercriticality), NOT the edge of chaos (lambda_max=0)
and NOT task optimisation.

Three pre-registered probes on a tanh recurrent reservoir:
  A. g-sweep, fixed low-dim input ensemble: does alpha fall monotonically with
     lambda_max? (scoped-sufficiency: a within-ensemble alpha(lambda) curve.)
  B. input-axis test at fixed g: vary input statistics (sigma_in). If sigma_in
     moves alpha INDEPENDENTLY of lambda (sign-reversed), the single-knob causal
     claim fails: alpha lives on a 2-D surface, not the lambda curve.
  C. DECISIVE falsifier(3): power-law input geometry at SUBCRITICAL g (lambda<0).
     If such a network reaches alpha~1 with lambda_max<0, the dynamical route is
     NOT necessary and the optimisation/geometry account (Stringer et al.) is not
     displaced -> the strong hypothesis is falsified (CON).

All numbers used in the digest come from this script -> 2026-06-07_cc_data.json.
"""
import json
import numpy as np
from scipy.stats import spearmanr


def reservoir_run(N=200, T=2000, g=1.0, sigma_in=0.5, din=3, U=None,
                  burn=300, seed=0):
    """Drive a tanh reservoir, return (lambda_max, alpha, PR).

    lambda_max: maximal Lyapunov exponent via a single renormalised tangent
    vector through the per-step Jacobian diag(1-x^2) * gW.
    alpha: power-law slope of the sorted covariance eigenspectrum, fitted in
    log-log over ranks [3, N/2].
    PR: participation ratio (sum ev)^2 / sum ev^2 -- spectrum non-degeneracy.
    """
    rng = np.random.default_rng(seed)
    W = rng.standard_normal((N, N)) / np.sqrt(N)
    if U is None:
        t = np.arange(T)
        fr = [0.03, 0.017, 0.011, 0.023, 0.007]
        U = np.vstack([np.sin(fr[i % 5] * t + i) for i in range(din)]).T
    Win = rng.standard_normal((N, U.shape[1]))
    x = np.zeros(N)
    Xs = []
    q = rng.standard_normal(N)
    q /= np.linalg.norm(q)
    ly = 0.0
    nl = 0
    for k in range(T):
        x = np.tanh(g * (W @ x) + sigma_in * (Win @ U[k]))
        D = 1.0 - x ** 2
        if k > burn:
            Xs.append(x.copy())
            q = (D[:, None] * (g * W)) @ q
            nr = np.linalg.norm(q)
            if nr > 0:
                ly += np.log(nr)
                q /= nr
                nl += 1
    X = np.array(Xs)
    X -= X.mean(0)
    C = (X.T @ X) / X.shape[0]
    ev = np.sort(np.linalg.eigvalsh(C))[::-1]
    ev = ev[ev > 1e-12]
    PR = float((ev.sum() ** 2) / (ev ** 2).sum())
    lo, hi = 3, min(len(ev), N // 2)
    r = np.arange(lo, hi)
    alpha = float(-np.polyfit(np.log(r), np.log(ev[lo - 1:hi - 1]), 1)[0])
    return ly / max(nl, 1), alpha, PR


def main():
    SEEDS = list(range(6))
    out = {}

    # ---- A. g-sweep, fixed low-dim input ensemble -----------------------
    g_grid = [0.7, 0.9, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]
    a_rows = []
    lam_all, al_all = [], []
    for g in g_grid:
        ls, as_, prs = [], [], []
        for s in SEEDS:
            l, a, pr = reservoir_run(g=g, din=3, sigma_in=0.5, seed=s)
            ls.append(l); as_.append(a); prs.append(pr)
            lam_all.append(l); al_all.append(a)
        a_rows.append({"g": g,
                       "lambda_max": float(np.mean(ls)),
                       "lambda_sd": float(np.std(ls)),
                       "alpha": float(np.mean(as_)),
                       "alpha_sd": float(np.std(as_)),
                       "PR": float(np.mean(prs))})
    out["g_sweep"] = a_rows
    out["g_sweep_spearman_lambda_alpha"] = float(
        spearmanr(lam_all, al_all).correlation)

    # ---- B. input-axis test at fixed g (sign reversal) ------------------
    g_fix = 1.5
    b_rows = []
    sig_list, lam_list, al_list = [], [], []
    for sig in [0.2, 0.5, 1.0, 2.0]:
        ls, as_, prs = [], [], []
        for s in SEEDS:
            l, a, pr = reservoir_run(g=g_fix, sigma_in=sig, din=5, seed=s)
            ls.append(l); as_.append(a); prs.append(pr)
        ml, ma = float(np.mean(ls)), float(np.mean(as_))
        b_rows.append({"sigma_in": sig, "lambda_max": ml, "alpha": ma,
                       "PR": float(np.mean(prs))})
        sig_list.append(sig); lam_list.append(ml); al_list.append(ma)
    out["input_axis"] = {"g_fixed": g_fix, "rows": b_rows,
                         "spearman_sigma_lambda":
                             float(spearmanr(sig_list, lam_list).correlation),
                         "spearman_sigma_alpha":
                             float(spearmanr(sig_list, al_list).correlation)}

    # ---- C. DECISIVE: power-law input geometry at subcritical g ----------
    rng = np.random.default_rng(7)
    T = 2000
    din_pl = 120
    Upl = rng.standard_normal((T, din_pl)) * (np.arange(1, din_pl + 1) ** (-0.5))
    c_rows = []
    for g in [0.3, 0.5, 0.8]:
        ls, as_, prs = [], [], []
        for s in SEEDS:
            l, a, pr = reservoir_run(g=g, U=Upl, sigma_in=0.8, seed=s + 100)
            ls.append(l); as_.append(a); prs.append(pr)
        c_rows.append({"g": g,
                       "lambda_max": float(np.mean(ls)),
                       "lambda_sd": float(np.std(ls)),
                       "alpha": float(np.mean(as_)),
                       "alpha_sd": float(np.std(as_)),
                       "PR": float(np.mean(prs))})
    out["decisive_powerlaw_subcritical"] = c_rows

    # decisive summary: is there a subcritical (lambda<0), non-degenerate
    # (PR>8) configuration with alpha within 0.15 of 1?
    hits = [r for r in c_rows
            if r["lambda_max"] < 0 and r["PR"] > 8 and abs(r["alpha"] - 1.0) < 0.15]
    out["decisive_summary"] = {
        "falsifier3_fires": bool(hits),
        "n_subcritical_alpha1_hits": len(hits),
        "min_lambda_among_hits": (min(r["lambda_max"] for r in hits)
                                  if hits else None),
        "alpha_tolerance": 0.15,
        "PR_min": 8}

    with open("2026-06-07_cc_data.json", "w") as f:
        json.dump(out, f, indent=2)

    # console summary
    print("=== A. g-sweep (fixed low-dim input) ===")
    print(f"{'g':>5}{'lambda':>9}{'alpha':>9}{'PR':>7}")
    for r in a_rows:
        print(f"{r['g']:5.1f}{r['lambda_max']:9.3f}{r['alpha']:9.3f}{r['PR']:7.1f}")
    print(f"Spearman(lambda,alpha) across g,seed = "
          f"{out['g_sweep_spearman_lambda_alpha']:+.3f}")
    print("\n=== B. input-axis at fixed g=1.5 ===")
    print(f"{'sig':>5}{'lambda':>9}{'alpha':>9}{'PR':>7}")
    for r in b_rows:
        print(f"{r['sigma_in']:5.1f}{r['lambda_max']:9.3f}{r['alpha']:9.3f}{r['PR']:7.1f}")
    print(f"Spearman(sigma,lambda) = {out['input_axis']['spearman_sigma_lambda']:+.3f}  "
          f"Spearman(sigma,alpha) = {out['input_axis']['spearman_sigma_alpha']:+.3f}")
    print("\n=== C. DECISIVE: power-law input, subcritical g ===")
    print(f"{'g':>5}{'lambda':>9}{'alpha':>9}{'PR':>7}")
    for r in c_rows:
        print(f"{r['g']:5.1f}{r['lambda_max']:9.3f}{r['alpha']:9.3f}{r['PR']:7.1f}")
    print(f"falsifier(3) fires: {out['decisive_summary']['falsifier3_fires']}  "
          f"hits={out['decisive_summary']['n_subcritical_alpha1_hits']}  "
          f"min_lambda={out['decisive_summary']['min_lambda_among_hits']}")


if __name__ == "__main__":
    main()
