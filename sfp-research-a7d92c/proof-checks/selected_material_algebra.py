"""Formal star identities and exact competitive-sublevel cutoff; no search."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sympy as sy
from direct_face_12_certificate import ref
from strong_face_exact_evidence import sqrt_bounds, matrix, inverse


def formal_identities():
    x, y, z, t = sy.symbols("x y z t", positive=True)
    d = sy.symbols("D1 D2 D3", positive=True)
    f = [x, y, z]
    Q = x*y+x*z+y*z
    E = t*(2*sy.eye(3)-sy.ones(3))+3*t/Q*sy.Matrix(f)*sy.Matrix(f).T
    checks = {}
    checks["det_E"] = sy.factor(E.det()-8*t**3) == 0
    adj = E.adjugate()
    checks["cofactors_E"] = all(
        sy.factor(adj[i, j] -
                  (3*t**2*(f[(i+1) % 3]+f[(i+2) % 3])**2/Q
                   if i == j else t**2*(3*f[3-i-j]**2/Q-1))) == 0
        for i in range(3) for j in range(3))
    K = sy.diag(*d)-E
    determinant = d[0]*d[1]*d[2]
    determinant -= t*sum(d[(i+1) % 3]*d[(i+2) % 3] *
                         (1+3*f[i]**2/Q) for i in range(3))
    determinant += 3*t**2/Q*sum(
        d[k]*(f[i]+f[j])**2 for i, j, k in [(0, 1, 2), (0, 2, 1), (1, 2, 0)])
    determinant -= 8*t**3
    checks["det_K"] = sy.factor(K.det()-determinant) == 0
    K_adj = K.adjugate()
    checks["cofactors_K"] = True
    for i in range(3):
        for j in range(3):
            if i == j:
                j1, k = (i+1) % 3, (i+2) % 3
                expected = (d[j1]*d[k]-d[j1]*E[k, k]-d[k]*E[j1, j1]
                            +3*t**2*(f[j1]+f[k])**2/Q)
            else:
                k = 3-i-j
                expected = d[k]*E[i, j]+t**2*(3*f[k]**2/Q-1)
            checks["cofactors_K"] &= sy.factor(K_adj[i, j]-expected) == 0
    b1, b2 = sy.symbols("b1 b2")
    bs = [b1, b2, -b1-b2]
    ps = [(t-b)/(3*t) for b in bs]
    checks["off_fixed_diagonal_derivative"] = all(
        sy.factor(sy.diff(t+(t-bs[j])*(t-bs[k])/(t-bs[i]), t)
                  -(ps[i]-ps[j]*ps[k])/ps[i]**2) == 0
        for i, j, k in [(0, 1, 2), (1, 0, 2), (2, 0, 1)])
    assert all(checks.values())
    return checks


def main():
    ap = argparse.ArgumentParser()
    for name in ("delta", "target", "direct-lower", "output"):
        ap.add_argument("--"+name, required=True)
    ap.add_argument("--digits", required=True, type=int)
    ap.add_argument("--budget")
    ap.add_argument("--counterexample-f", nargs=3)
    a = ap.parse_args()
    delta, target, declared = F(a.delta), F(a.target), F(a.direct_lower)
    assert 0 < delta <= F(1, 100)
    C, vectors = ref(delta)
    vectors.append([vectors[0][i]-vectors[1][i] for i in range(3)])
    lower = upper = F(0)
    for v in vectors:
        lo, hi = sqrt_bounds(sum((v[i]/C[i])**2 for i in range(3)), a.digits)
        lower += lo
        upper += hi
    assert target < declared < lower
    # Convex quadratic on the r_ij simplex: its maximum is at a vertex.
    frobenius2 = max(5+7*delta**2, 2+10*delta**2)
    coefficient = F(9, 4)
    assert frobenius2 < coefficient**2
    floor = C[0]*(declared/target-1)/coefficient
    out = {
        "formal_identities": formal_identities(),
        "delta": str(delta), "target": str(target),
        "direct_lower_declared": str(declared),
        "direct_length_interval": [str(lower), str(upper)],
        "off_diagonal_norm_coefficient": str(coefficient),
        "strict_t_floor": str(floor),
        "strict_f_ratio_floors": [str(floor/c) for c in C],
        "scope": "Necessary competitive-sublevel bounds; not material saturation",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    if a.counterexample_f:
        point = list(map(F, a.counterexample_f))
        assert all(0 < point[i] < C[i] for i in range(3))
        K, mass = matrix(point, C)
        inv = inverse(K)
        Q = sum(point[i]*point[j] for i, j in [(0, 1), (0, 2), (1, 2)])
        W = [(Q-point[i]**2)/(point[(i+1) % 3]*point[(i+2) % 3])
             for i in range(3)]
        forms = []
        lo = hi = F(0)
        for v in vectors:
            u = [sum(inv[i][j]*v[j] for j in range(3)) for i in range(3)]
            forms.append(sum(u[i]*inv[i][j]*W[j]*u[j]
                             for i in range(3) for j in range(3)))
            l, h = sqrt_bounds(sum(z*z for z in u), a.digits)
            lo += l
            hi += h
        assert a.budget and mass < F(a.budget) and hi < target
        assert any(w < 0 for w in W) and all(q > 0 for q in forms)
        out["competitive_spd_counterexample"] = {
            "f": list(map(str, point)), "mass": str(mass),
            "budget": a.budget, "ell_interval": [str(lo), str(hi)],
            "W": list(map(str, W)), "special_forms": list(map(str, forms)),
            "all_special_forms_positive": True,
            "Jordan_has_negative_diagonal": True,
        }
    Path(a.output).write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
