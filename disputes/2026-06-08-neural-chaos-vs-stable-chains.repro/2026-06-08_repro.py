#!/usr/bin/env python3
"""Duellum Veritatis No.6 — reproducible compute.

Decisive question of the duel: can stereotyped neural sequences (zebra-finch
HVC song, hippocampal replay, cortical preparatory sequences) be the signature
of DETERMINISTIC chaotic itinerancy with a positive leading Lyapunov exponent
(lambda_1 > 0) acting as the SOURCE of timing variability -- or is the observed
phenomenology (rigid transition order, variable transition times, low CV)
equally produced by a stable adaptation-clocked chain (lambda_1 <= 0) with
injected noise?

All numbers are synthetic / analytic toy models calibrated to textbook
zebra-finch HVC values (order stereotypy > 99%, syllable-duration CV ~ 5-15%,
sub-millisecond spike-timing precision over a ~1 s song). They probe whether the
chaotic mechanism is NECESSARY in principle; they are NOT measurements on neural
data. paper_faithful = false.
"""
import json
import hashlib
import numpy as np

OUT = "2026-06-08_cc_data.json"


def stable_adaptation_chain():
    """Falsifier arm (b): a stable chain clocked by an adaptation variable
    crossing threshold (lambda_1 <= 0) reproduces rigid order + variable,
    low-CV durations -- the very phenomenology the SCO thesis claims as its
    signature. Transitions are a clock (adaptation reaching threshold), NOT a
    Poisson escape, so CV is low and order errors are zero."""
    rng = np.random.default_rng(0)
    K, tau, sigma, N = 5, 0.15, 0.012, 8000
    intervals = tau + sigma * rng.standard_normal((N, K))
    order_errors = int((intervals <= 0).sum())
    cv = float(intervals.std() / intervals.mean())
    return {
        "K_links": K,
        "mean_interval_ms": float(intervals.mean() * 1e3),
        "sigma_ms": sigma * 1e3,
        "n_trials": N,
        "cv_intervals": cv,
        "order_errors": order_errors,
    }


def poisson_escape_cv():
    """The straw-man PRO attributed to the noise account: independent Poisson
    escape between metastable states gives an exponential interval distribution
    with CV = 1 -- far above observed CV ~ 0.1. CON's point: the real noise
    account is an adaptation CLOCK, not Poisson escape, so this number does NOT
    discriminate the hypotheses; it only refutes a caricature."""
    rng = np.random.default_rng(11)
    n = 400000
    rate = 1.0 / 0.15
    intervals = rng.exponential(1.0 / rate, n)
    return {"cv_poisson_escape": float(intervals.std() / intervals.mean())}


def jitter_budget(T, label):
    """Continuous-noise timing variance to time T under a leading exponent
    lambda: V(T) = D*(exp(2*lambda*T)-1)/(2*lambda); lambda->0 gives diffusion
    V = D*T. D is calibrated so that at lambda->0 the end-of-song jitter equals
    1 ms (the observed sub-ms scale). A positive lambda is then an AMPLIFIER of
    that noise, and we read how large the end-point jitter becomes."""
    D = 1e-6  # s^2/s, so sqrt(D*T) = 1 ms at T = 1 s, lambda = 0
    rows = []
    for lam in (0.0, 0.5, 1.0, 2.0, 5.0, 10.0):
        V = D * T if lam == 0 else D * (np.exp(2 * lam * T) - 1) / (2 * lam)
        rows.append({"lambda_per_s": lam, "jitter_ms": float(np.sqrt(V) * 1e3)})
    return {"window_s": T, "label": label, "calibration_D": D, "rows": rows}


def saddle_exit_decomposition():
    """CON's decisive analytic result. In PRO's own saddle-exit model the exit
    time is tau = (1/lambda)*ln(a/x0) with x0 = eps*|z|, z ~ N(0,1). Then
    Var(tau) = Var(ln|z|)/lambda^2 -- INDEPENDENT of the noise scale eps and of
    the diffusion D. So the 'attractor-geometry' dispersion PRO offered as a
    discriminator is just log-compressed initial-condition noise, not a
    signature of deterministic chaos."""
    rng = np.random.default_rng(7)
    z = np.abs(rng.normal(0, 1, 5_000_000))
    ln = np.log(z)
    var_ln = float(ln.var())
    std_ln = float(ln.std())

    # eps -> 0 : with no noise in the initial condition the variance vanishes at
    # ANY lambda, so chaos is not the SOURCE of the variability -- noise is.
    lam = 5.0
    a = 0.1
    eps_rows = []
    for eps in (1e-2, 1e-4, 1e-8, 0.0):
        if eps == 0.0:
            x0 = np.full(300000, 1e-3)
        else:
            x0 = np.abs(rng.normal(0, eps, 300000))
        x0 = np.clip(x0, 1e-300, a * 0.999)
        tau = (1.0 / lam) * np.log(a / x0)
        eps_rows.append({
            "eps": eps,
            "mean_ms": float(tau.mean() * 1e3),
            "std_ms": float(tau.std() * 1e3),
        })
    return {"var_ln_abs_z": var_ln, "std_ln_abs_z": std_ln,
            "lambda_for_eps_sweep": lam, "separatrix_a": a, "eps_rows": eps_rows}


def lambda_lock(std_ln):
    """The non-decoupling lock. To make the saddle-exit mechanism produce the
    observed duration variability, mean and CV JOINTLY fix lambda:
    lambda = std(ln|z|) / (CV * mean). The implied lambda then drives an
    amplification exp(lambda*mean) over one transition window. A realistic CV
    forces lambda ~ 50-220/s, whose amplification (~10^3) would shatter the
    sub-millisecond spike-timing precision that cooling and Hahnloser (2002)
    confirm directly. The two falsifier arms cannot be satisfied at once."""
    rows = []
    for mean_ms, cv in ((50, 0.15), (150, 0.15), (50, 0.10)):
        mean_s = mean_ms / 1e3
        lam = std_ln / (cv * mean_s)
        amp = float(np.exp(lam * mean_s))
        implied_jitter_ms = float(std_ln / lam * 1e3)
        rows.append({
            "mean_ms": mean_ms, "cv": cv,
            "lambda_req_per_s": float(lam),
            "amplification_over_window": amp,
            "implied_jitter_ms": implied_jitter_ms,
        })
    return rows


def main():
    data = {
        "_about": "Duellum Veritatis No.6 reproducible compute. Synthetic/analytic "
                  "toy models calibrated to zebra-finch HVC literature values; "
                  "probes in-principle sufficiency/necessity, NOT neural-data "
                  "measurement. paper_faithful=false.",
        "stable_adaptation_chain": stable_adaptation_chain(),
        "poisson_escape": poisson_escape_cv(),
        "jitter_full_song": jitter_budget(1.0, "full song ~1 s"),
        "jitter_transition_window": jitter_budget(0.05, "single transition ~50 ms"),
        "saddle_exit": saddle_exit_decomposition(),
    }
    data["lambda_lock"] = lambda_lock(data["saddle_exit"]["std_ln_abs_z"])
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("wrote", OUT)
    print("sha256:" + hashlib.sha256(open(OUT, "rb").read()).hexdigest())
    # echo headline numbers
    c = data["stable_adaptation_chain"]
    print(f"chain: CV={c['cv_intervals']:.4f} order_errors={c['order_errors']}")
    print("poisson escape CV =", round(data["poisson_escape"]["cv_poisson_escape"], 3))
    for r in data["jitter_full_song"]["rows"]:
        print(f"  full-song lambda={r['lambda_per_s']:>4}/s jitter={r['jitter_ms']:.2f} ms")
    for r in data["jitter_transition_window"]["rows"]:
        if r["lambda_per_s"] in (5.0, 10.0):
            print(f"  50ms-window lambda={r['lambda_per_s']:>4}/s jitter={r['jitter_ms']:.3f} ms")
    print("Var(ln|z|) =", round(data["saddle_exit"]["var_ln_abs_z"], 4),
          "std =", round(data["saddle_exit"]["std_ln_abs_z"], 4))
    for r in data["lambda_lock"]:
        print(f"  lock mean={r['mean_ms']}ms CV={r['cv']}: "
              f"lambda={r['lambda_req_per_s']:.1f}/s "
              f"amp={r['amplification_over_window']:.2e} "
              f"implied_jitter={r['implied_jitter_ms']:.1f}ms")
    for r in data["saddle_exit"]["eps_rows"]:
        print(f"  eps={r['eps']:>8}: mean={r['mean_ms']:.1f}ms std={r['std_ms']:.2f}ms")


if __name__ == "__main__":
    main()
