#!/usr/bin/env python3
"""Duellum Veritatis No.10 — reproducible compute bundle.

Frozen claim (PRO): connectome controllability metrics carry target-ranking
information beyond degree and strength.

This script reproduces the decisive substrate of the duel: a modular
stochastic-block connectome (n=200, K=8) with PLANTED connector hubs — the
topology most favourable to the PRO mechanism (topological path diversity).
The ground-truth target is the planted hub set, which is NOT derived from any
controllability metric. We test whether average/modal controllability add
held-out ranking power for that target ABOVE degree and strength.

All published numbers come from this script -> 2026-06-12_cc_data.json.
"""
import json
import numpy as np
import networkx as nx
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.preprocessing import StandardScaler

SEED = 11
np.random.seed(SEED)

# ---- build modular SBM with planted connector hubs (PRO-friendly substrate) --
n, K = 200, 8
sz = n // K
comm = np.repeat(np.arange(K), sz)
p_in, p_out = 0.35, 0.01
A = np.zeros((n, n))
for i in range(n):
    for j in range(i + 1, n):
        p = p_in if comm[i] == comm[j] else p_out
        if np.random.rand() < p:
            A[i, j] = A[j, i] = np.random.lognormal(-1.5, 1.0)
# plant 25 connector hubs: nodes bridging modules by construction (ground truth)
hubs = np.random.choice(n, 25, replace=False)
hubset = set(hubs.tolist())
for h in hubs:
    for o in np.random.choice(n, 12, replace=False):
        if comm[o] != comm[h] and A[h, o] == 0:
            A[h, o] = A[o, h] = np.random.lognormal(-1.0, 1.0)
G = nx.from_numpy_array(A)
if not nx.is_connected(G):
    for u, v in nx.minimum_spanning_tree(G).edges():
        if A[u, v] == 0:
            A[u, v] = A[v, u] = 0.01


def controllability(M):
    """Average and modal controllability (corrected modal formula:
    weight by (1 - lambda^2), NOT divide by squared eigenvector component)."""
    mx = np.max(np.real(np.linalg.eigvals(M)))
    Mn = M / (1 + mx + 0.1)
    w, v = np.linalg.eig(Mn)
    w, v = np.real(w), np.real(v)
    avg = np.array([np.sum(v[j, :] ** 2 / (1 - w ** 2 + 1e-9)) for j in range(M.shape[0])])
    mod = np.array([np.sum((1 - w ** 2) * v[j, :] ** 2) for j in range(M.shape[0])])
    return avg, mod


avg, mod = controllability(A)
deg = np.sum(A > 0, 1).astype(float)
strg = np.sum(A, 1)
y = np.array([1 if i in hubset else 0 for i in range(n)])

# ---- rank-space redundancy: is controllability just strength, re-labelled? ---
sp_avg_strg = float(spearmanr(avg, strg).correlation)
sp_mod_strg = float(spearmanr(mod, strg).correlation)
sp_avg_mod = float(spearmanr(avg, mod).correlation)
top_strg = set(np.argsort(strg)[-30:].tolist())
top_avg = set(np.argsort(avg)[-30:].tolist())
overlap_top30 = len(top_strg & top_avg)

# ---- held-out ranking: does controllability add AUC over degree+strength? ----
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=1)


def cv_auc(X, yv):
    a = []
    for tr, te in cv.split(X, yv):
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(max_iter=2000).fit(sc.transform(X[tr]), yv[tr])
        a.append(roc_auc_score(yv[te], clf.predict_proba(sc.transform(X[te]))[:, 1]))
    return np.array(a)


X_ds = np.column_stack([deg, strg])
X_nl = np.column_stack([strg, strg ** 2, np.log(strg + 1e-6), deg])
X_full = np.column_stack([deg, strg, avg, mod])
a_ds, a_nl, a_full = cv_auc(X_ds, y), cv_auc(X_nl, y), cv_auc(X_full, y)
delta = float(a_full.mean() - a_ds.mean())

# bootstrap 95% CI on delta AUC (full vs degree+strength)
boot = []
rng = np.random.default_rng(SEED)
for _ in range(500):
    idx = rng.choice(n, n, replace=True)
    if y[idx].sum() < 3 or y[idx].sum() > n - 3:
        continue
    boot.append(cv_auc(X_full[idx], y[idx]).mean() - cv_auc(X_ds[idx], y[idx]).mean())
boot = np.array(boot)
ci_low, ci_high = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))

# degree-preserving null: does a rewired graph reproduce the controllability delta?
null_deltas = []
for s in range(40):
    Gb = nx.from_numpy_array((A > 0).astype(float))
    try:
        Gb = nx.double_edge_swap(Gb, nswap=5 * Gb.number_of_edges(), max_tries=50 * Gb.number_of_edges(), seed=s)
    except nx.NetworkXAlgorithmError:
        pass
    An = nx.to_numpy_array(Gb)
    # re-attach the empirical weight multiset to surviving edges
    wts = A[np.triu(A, 1) > 0]
    rng.shuffle(wts)
    ii, jj = np.where(np.triu(An, 1) > 0)
    m = min(len(ii), len(wts))
    Aw = np.zeros((n, n))
    for k in range(m):
        Aw[ii[k], jj[k]] = Aw[jj[k], ii[k]] = wts[k]
    av_n, mo_n = controllability(Aw)
    Xf_n = np.column_stack([np.sum(Aw > 0, 1), np.sum(Aw, 1), av_n, mo_n])
    Xd_n = np.column_stack([np.sum(Aw > 0, 1), np.sum(Aw, 1)])
    null_deltas.append(float(cv_auc(Xf_n, y).mean() - cv_auc(Xd_n, y).mean()))
null_deltas = np.array(null_deltas)
empirical_above_null = float(np.mean(delta > null_deltas))

data = {
    "substrate": "modular_SBM_planted_connector_hubs",
    "n_nodes": n, "n_modules": K, "n_planted_hubs": 25,
    "seed": SEED,
    "rank_redundancy": {
        "spearman_avg_ctrl_vs_strength": round(sp_avg_strg, 3),
        "spearman_modal_ctrl_vs_strength": round(sp_mod_strg, 3),
        "spearman_avg_vs_modal": round(sp_avg_mod, 3),
        "top30_overlap_strength_vs_avg_ctrl": overlap_top30,
    },
    "auc_planted_hub_target": {
        "degree_strength_mean": round(float(a_ds.mean()), 4),
        "degree_strength_std": round(float(a_ds.std()), 4),
        "strength_nonlinear_mean": round(float(a_nl.mean()), 4),
        "strength_nonlinear_std": round(float(a_nl.std()), 4),
        "full_with_controllability_mean": round(float(a_full.mean()), 4),
        "full_with_controllability_std": round(float(a_full.std()), 4),
        "delta_auc_full_minus_degstr": round(delta, 4),
        "delta_auc_bootstrap_ci95": [round(ci_low, 4), round(ci_high, 4)],
        "ci_excludes_zero": bool(ci_low > 0 or ci_high < 0),
    },
    "degree_preserving_null": {
        "n_null_graphs": int(len(null_deltas)),
        "null_delta_mean": round(float(null_deltas.mean()), 4),
        "null_delta_std": round(float(null_deltas.std()), 4),
        "empirical_above_null_fraction": round(empirical_above_null, 3),
    },
    "registered_thresholds": {
        "pro_accept": "delta >= 0.05 AUC AND bootstrap 95% CI excludes zero AND null does not reproduce",
        "pro_reject": "degree/strength matches full within +/-0.02 OR R2(ctrl ~ deg+str) >= 0.95",
    },
}

with open("2026-06-12_cc_data.json", "w") as f:
    json.dump(data, f, indent=2)
print(json.dumps(data, indent=2))
