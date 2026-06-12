#!/usr/bin/env python3
"""Duellum Veritatis No.8 reproduction.

Thesis under test: in non-Hermitian (non-normal) connectivity matrices the
transient dynamics and effective memory are governed by NON-NORMALITY of the
operator (pseudospectrum / Kreiss constant / numerical radius), not by the
eigenvalue spectrum. Two ensembles with an IDENTICAL spectrum but different
non-normality should show systematically different transient amplification and
memory.

Everything below is deterministic (fixed seeds). All numbers that appear in the
explainer come from the cc_data.json this script writes.
"""
import json
import numpy as np

SEED = 17
rng = np.random.default_rng(SEED)


# ----------------------------------------------------------------------------
# operator diagnostics
# ----------------------------------------------------------------------------
def spectral_radius(A):
    return float(np.max(np.abs(np.linalg.eigvals(A))))


def departure(A):
    """Henrici departure from normality: sqrt(||A||_F^2 - sum|eig|^2)."""
    e = np.linalg.eigvals(A)
    val = np.linalg.norm(A, "fro") ** 2 - np.sum(np.abs(e) ** 2)
    return float(np.sqrt(max(val, 0.0)))


def sup_transient(A, tmax=400):
    """sup_t ||A^t||_2 over t = 1..tmax (transient amplification)."""
    Ak = np.eye(A.shape[0])
    best = 0.0
    for _ in range(1, tmax + 1):
        Ak = Ak @ A
        n = np.linalg.norm(Ak, 2)
        if n > best:
            best = n
        if n > 1e18:  # diverged (spectral radius > 1); stop early
            break
    return float(best)


def numerical_radius(A, n_angles=180):
    """w(A) = max_theta lambda_max( Hermitian part of e^{-i theta} A )."""
    best = 0.0
    for th in np.linspace(0, np.pi, n_angles, endpoint=False):
        M = np.exp(-1j * th) * A
        H = 0.5 * (M + M.conj().T)
        lam = float(np.max(np.linalg.eigvalsh(H)))
        if lam > best:
            best = lam
    return best


def kreiss_constant(A, n_r=24, n_ang=72):
    """K(A) = sup_{|z|>1} (|z|-1) ||(zI - A)^{-1}||_2 over a grid outside the
    unit circle (discrete-time Kreiss constant)."""
    N = A.shape[0]
    I = np.eye(N, dtype=complex)
    radii = 1.0 + np.concatenate([np.linspace(0.002, 0.2, n_r // 2),
                                  np.linspace(0.2, 2.0, n_r - n_r // 2)])
    angs = np.linspace(0, 2 * np.pi, n_ang, endpoint=False)
    best = 0.0
    for r in radii:
        for a in angs:
            z = r * np.exp(1j * a)
            R = np.linalg.norm(np.linalg.inv(z * I - A), 2)
            val = (r - 1.0) * R
            if val > best:
                best = val
    return float(best)


# ----------------------------------------------------------------------------
# spectrum-preserving non-normal family (real Schur form, exact spectrum)
# ----------------------------------------------------------------------------
def real_orthogonal(N, rng):
    Q, _ = np.linalg.qr(rng.standard_normal((N, N)))
    return Q


def block_diag_schur(N, rho):
    """Block-diagonal real Schur D: conjugate-pair eigenvalues of modulus rho on
    a ring. Eigenvalues are exactly {rho e^{+/- i a}}."""
    D = np.zeros((N, N))
    k = 0
    for a in np.linspace(0.2, np.pi - 0.2, N // 2):
        re, im = rho * np.cos(a), rho * np.sin(a)
        D[k, k] = re
        D[k + 1, k + 1] = re
        D[k, k + 1] = im
        D[k + 1, k] = -im
        k += 2
    if k < N:  # odd N: one real eigenvalue
        D[k, k] = rho * 0.5
    return D


def block_upper_mask(N, bs=2):
    """1 where column-block index > row-block index (strictly block-upper).
    Adding such a perturbation to a block-diagonal real Schur form leaves the
    diagonal 2x2 blocks -- hence the spectrum -- EXACTLY unchanged."""
    idx = np.arange(N) // bs
    return (idx[None, :] > idx[:, None]).astype(float)


def build_fixed_spectrum(N, rho, Q, Tblock, s):
    """A = Q (D + s*Tblock) Q^T. D block-diagonal real Schur; Tblock strictly
    block-upper-triangular -> raises non-normality while the spectrum is held
    EXACTLY fixed (eigenvalues = D's diagonal blocks for any s)."""
    D = block_diag_schur(N, rho)
    return Q @ (D + s * Tblock) @ Q.T, D


# ============================================================================
# Experiment A: at FIXED spectrum, sweep non-normality, track transients
# ============================================================================
def experiment_A():
    N = 100
    rho = 0.85
    Q = real_orthogonal(N, rng)
    Tblock = np.triu(rng.standard_normal((N, N)), 1) * block_upper_mask(N)
    Tblock /= np.linalg.norm(Tblock, 2)  # normalise so s sets the scale
    s_grid = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    rows = []
    for s in s_grid:
        A, _ = build_fixed_spectrum(N, rho, Q, Tblock, s)
        rows.append({
            "s": float(s),
            "spectral_radius": spectral_radius(A),
            "departure": departure(A),
            "sup_transient": sup_transient(A),
            "numerical_radius": numerical_radius(A),
            "kreiss": kreiss_constant(A),
        })
    return {"N": N, "rho_target": rho, "rows": rows}


# ============================================================================
# Experiment B: is the pseudospectral measure (Kreiss) a sufficient statistic
# for transient amplification? Pool points where BOTH spectrum and non-normality
# vary, regress log(sup) on each candidate predictor.
# ============================================================================
def r2(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    A = np.vstack([x, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = A @ coef
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return float(1 - ss_res / ss_tot)


def experiment_B():
    N = 80
    pool = []
    for rho in (0.6, 0.75, 0.85, 0.92):
        Q = real_orthogonal(N, rng)
        Tblock = np.triu(rng.standard_normal((N, N)), 1) * block_upper_mask(N)
        Tblock /= np.linalg.norm(Tblock, 2)
        for s in (0.5, 1.5, 3.0, 5.0):
            A, _ = build_fixed_spectrum(N, rho, Q, Tblock, s)
            sup = sup_transient(A, tmax=300)
            pool.append({
                "rho": spectral_radius(A),
                "departure": departure(A),
                "kreiss": kreiss_constant(A),
                "numrad": numerical_radius(A),
                "sup": sup,
            })
    eps = 1e-12
    logsup = [np.log(p["sup"] + eps) for p in pool]
    r2_kreiss = r2([np.log(p["kreiss"] + eps) for p in pool], logsup)
    r2_numrad = r2([np.log(p["numrad"] + eps) for p in pool], logsup)
    r2_departure = r2([np.log(p["departure"] + eps) for p in pool], logsup)
    r2_rho = r2([p["rho"] for p in pool], logsup)
    return {
        "N": N,
        "n_points": len(pool),
        "r2_log_sup_on_log_kreiss": r2_kreiss,
        "r2_log_sup_on_log_numrad": r2_numrad,
        "r2_log_sup_on_log_departure": r2_departure,
        "r2_log_sup_on_spectral_radius": r2_rho,
        "pool": pool,
    }


# ============================================================================
# Experiment C: memory at IDENTICAL spectrum. Normal operator vs a chain
# (delay-line) non-normal operator sharing the same eigenvalues. Linear memory
# capacity measured under input noise (Ganguli-Sompolinsky style).
# ============================================================================
def memory_capacity(A, win, n_steps=4000, washout=300, kmax=60, noise=1e-2,
                    seed=0):
    """Linear short-term memory capacity of a discrete reservoir
    x(t+1) = A x(t) + win * u(t) + noise, reconstruct u(t-k) by ridge."""
    g = np.random.default_rng(seed)
    N = A.shape[0]
    u = g.standard_normal(n_steps)
    X = np.zeros((n_steps, N))
    x = np.zeros(N)
    for t in range(n_steps - 1):
        x = A @ x + win * u[t] + noise * g.standard_normal(N)
        X[t + 1] = x
    Xw = X[washout:]
    uw = u[washout:]
    mc = 0.0
    lam = 1e-4
    G = Xw.T @ Xw + lam * np.eye(N)
    Ginv = np.linalg.inv(G)
    for k in range(1, kmax + 1):
        target = uw[:-k] if k > 0 else uw
        Xk = Xw[k:]
        w = Ginv @ (Xk.T @ target)
        pred = Xk @ w
        c = np.corrcoef(pred, target)[0, 1]
        if np.isfinite(c):
            mc += c * c
    return float(mc)


def experiment_C():
    N = 100
    rho = 0.9
    Q = real_orthogonal(N, rng)
    Dn = block_diag_schur(N, rho)          # normal operator, departure ~ 0
    A_normal = Q @ Dn @ Q.T
    # chain / delay-line: couple each block to the next (super-block-diagonal).
    # This strictly-block-upper term raises non-normality while leaving the
    # spectrum EXACTLY equal to Dn's (identical eigenvalues for both operators).
    C = np.zeros((N, N))
    for j in range(0, N - 2, 2):
        C[j, j + 2] = 1.0
        C[j + 1, j + 3] = 1.0
    A_chain = Q @ (Dn + 0.6 * C) @ Q.T
    win = rng.standard_normal(N)
    win /= np.linalg.norm(win)
    out = {
        "N": N,
        "rho_target": rho,
        "normal": {
            "spectral_radius": spectral_radius(A_normal),
            "departure": departure(A_normal),
            "kreiss": kreiss_constant(A_normal),
            "memory_capacity": memory_capacity(A_normal, win, seed=1),
        },
        "chain": {
            "spectral_radius": spectral_radius(A_chain),
            "departure": departure(A_chain),
            "kreiss": kreiss_constant(A_chain),
            "memory_capacity": memory_capacity(A_chain, win, seed=1),
        },
    }
    return out


def main():
    data = {
        "schema": "duellum.cc_data.v1",
        "duel": "no8 2026-06-10 non-Hermitian spectrum vs non-normality",
        "seed": SEED,
        "experiment_A_fixed_spectrum_transient_sweep": experiment_A(),
        "experiment_B_kreiss_sufficient_statistic": experiment_B(),
        "experiment_C_memory_identical_spectrum": experiment_C(),
    }
    with open("2026-06-10_cc_data.json", "w") as f:
        json.dump(data, f, indent=2)
    # console summary
    A = data["experiment_A_fixed_spectrum_transient_sweep"]
    print("== Experiment A: fixed spectrum, sweep non-normality ==")
    print("  rho fixed at", A["rho_target"])
    for r in A["rows"]:
        print(f"  s={r['s']:>4}  rho={r['spectral_radius']:.4f}  "
              f"dep={r['departure']:7.3f}  sup||A^t||={r['sup_transient']:.3f}  "
              f"w(A)={r['numerical_radius']:.3f}  K={r['kreiss']:.3f}")
    B = data["experiment_B_kreiss_sufficient_statistic"]
    print("== Experiment B: predictors of log sup||A^t|| (%d points) ==" % B["n_points"])
    print(f"  R^2 on log Kreiss     = {B['r2_log_sup_on_log_kreiss']:.3f}")
    print(f"  R^2 on log num.radius = {B['r2_log_sup_on_log_numrad']:.3f}")
    print(f"  R^2 on log departure  = {B['r2_log_sup_on_log_departure']:.3f}")
    print(f"  R^2 on spectral radius= {B['r2_log_sup_on_spectral_radius']:.3f}")
    C = data["experiment_C_memory_identical_spectrum"]
    print("== Experiment C: memory at IDENTICAL spectrum ==")
    print(f"  normal: rho={C['normal']['spectral_radius']:.4f} dep={C['normal']['departure']:.3f} MC={C['normal']['memory_capacity']:.2f}")
    print(f"  chain : rho={C['chain']['spectral_radius']:.4f} dep={C['chain']['departure']:.3f} MC={C['chain']['memory_capacity']:.2f}")


if __name__ == "__main__":
    main()
