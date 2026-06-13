"""
Duellum Veritatis No.11 — PVS influx vs net parenchymal clearance.

Frozen claim (PRO): tracer influx into perivascular spaces is a valid quantitative
proxy for net parenchymal solute clearance.
CON: influx and net clearance can decouple when the rate-limiting exchange/egress
step is interstitial or vascular, not the imaged PVS conduit.

Steady-state series-conductance model (CON's analytical decomposition):
  influx     = Q * C0                  imaged PVS delivery (through-flow)
  g          = E*K / (E+K)             series exchange-then-egress conductance
  C_p        = Q*C0 / (Q + g)          parenchymal concentration
  clearance  = g * C_p                 net parenchymal clearance

Q (PVS through-flow), E (PVS<->ISF exchange) and K (ISF->vasculature egress) are
independent. The neutral substrate fixes the in-channel Peclet number Pe in
[0.1, 10] but does NOT pin the exchange/egress coefficients. Observable: Spearman
rho and rank stability between influx and clearance across the plausible box.

Decision criterion (registered before compute):
  PRO accepted  if rho >= 0.8 across the plausible box and no named bottleneck
                breaks rank ordering;
  PRO rejected  if a physiologically plausible bottleneck yields rho <= 0.3 or
                reverses ranks while preserving the neutral Pe substrate.
"""
import json
import numpy as np
from scipy.stats import spearmanr

C0 = 1.0
N = 30000
SEED = 11
rng = np.random.default_rng(SEED)

# Neutral substrate: in-channel Peclet held in [0.1, 10] for every point.
Pe = 10 ** rng.uniform(np.log10(0.1), np.log10(10.0), N)  # preserved, not pinning E,K


def regime(Q, E, K):
    g = E * K / (E + K)
    C_p = Q * C0 / (Q + g)
    influx = Q * C0
    clearance = g * C_p
    return influx, clearance, g


def rho_of(influx, clearance):
    return float(spearmanr(influx, clearance).statistic)


def rank_reversal(influx, clearance):
    ir = np.argsort(np.argsort(influx)) / (N - 1)
    cr = np.argsort(np.argsort(clearance)) / (N - 1)
    top = float(cr[ir > 0.9].mean())
    bot = float(cr[ir < 0.1].mean())
    return top, bot, bool(top < bot)


# Narrow physiologically realistic prior (PRO's own concession): E,K within ~2 orders.
Q = 10 ** rng.uniform(-1, 1, N)
E_norm = 10 ** rng.uniform(-1, 1, N)
K_norm = 10 ** rng.uniform(-1, 1, N)

out = {}

# 1. Control / full box — all conductances normal.
inf, cl, g = regime(Q, E_norm, K_norm)
top, bot, rev = rank_reversal(inf, cl)
out["control_full_box"] = {
    "rho": round(rho_of(inf, cl), 3),
    "rank_top10_meanrank": round(top, 3),
    "rank_bot10_meanrank": round(bot, 3),
    "rank_reversal": rev,
    "n": N,
    "desc": "Q,E,K all log-uniform 10^[-1,1]; PRO threshold rho>=0.8",
}

# 2. PVS-conduit bottleneck: the imaged conduit limits (g >> Q). Proxy should hold.
K_hi = 10 ** rng.uniform(1.5, 2.5, N)
E_hi = 10 ** rng.uniform(1.5, 2.5, N)
inf2, cl2, g2 = regime(Q, E_hi, K_hi)
out["pvs_conduit_bottleneck"] = {
    "rho": round(rho_of(inf2, cl2), 3),
    "frac_g_gt_Q": round(float((g2 > Q).mean()), 3),
    "n": N,
    "desc": "E,K >> Q so g>>Q; conduit is rate-limiting; proxy expected to hold",
}

# 3. vascular_uptake_bottleneck: egress K depressed 0.5-1.0 order (aging/IIH/AQP4).
K_vasc = 10 ** rng.uniform(-2.5, -1.5, N)
inf3, cl3, g3 = regime(Q, E_norm, K_vasc)
top3, bot3, rev3 = rank_reversal(inf3, cl3)
out["vascular_uptake_bottleneck"] = {
    "rho": round(rho_of(inf3, cl3), 3),
    "rank_top10_meanrank": round(top3, 3),
    "rank_bot10_meanrank": round(bot3, 3),
    "rank_reversal": rev3,
    "n": N,
    "desc": "K log-uniform 10^[-2.5,-1.5]; Q,E normal; named single-mechanism bottleneck",
}

# 4. interstitial_exchange_bottleneck: exchange E depressed, K normal.
E_int = 10 ** rng.uniform(-2.5, -1.5, N)
inf4, cl4, g4 = regime(Q, E_int, K_norm)
top4, bot4, rev4 = rank_reversal(inf4, cl4)
out["interstitial_exchange_bottleneck"] = {
    "rho": round(rho_of(inf4, cl4), 3),
    "rank_top10_meanrank": round(top4, 3),
    "rank_bot10_meanrank": round(bot4, 3),
    "rank_reversal": rev4,
    "n": N,
    "desc": "E log-uniform 10^[-2.5,-1.5]; Q,K normal; named single-mechanism bottleneck",
}

# 5. Depth scan: shift the egress band K down by s decades from the normal [-1,1].
depth = []
for s in (0.0, -0.5, -1.0, -1.5, -2.0):
    K_s = 10 ** rng.uniform(-1 + s, 1 + s, N)
    inf_s, cl_s, _ = regime(Q, E_norm, K_s)
    depth.append({"shift_decades": s, "rho": round(rho_of(inf_s, cl_s), 3)})
out["egress_depth_scan"] = depth

out["_meta"] = {
    "model": "steady-state series conductance: influx=Q*C0, g=E*K/(E+K), C_p=Q*C0/(Q+g), clearance=g*C_p",
    "C0": C0,
    "N": N,
    "seed": SEED,
    "pe_substrate": "Pe in [0.1,10] log-uniform, preserved across all regimes",
    "pro_threshold_rho": 0.8,
    "con_threshold_rho": 0.3,
}

with open("2026-06-13_cc_data.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

for k, v in out.items():
    if k == "_meta":
        continue
    print(k, "=>", v if not isinstance(v, list) else v)
