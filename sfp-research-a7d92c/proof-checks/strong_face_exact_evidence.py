"""Exact reference/witness evidence; no optimization or trajectory integration."""
import argparse
import hashlib
import json
from fractions import Fraction as F
from math import isqrt
from pathlib import Path


def matrix(f, target):
    x, y, z = f
    h = [x+y+x*y/z, x+z+x*z/y, y+z+y*z/x]
    total = sum(h)
    pairs = [(0, 1), (0, 2), (1, 2)]
    jac = [[f[k] * (F(e in pair)/h[e] - 1/total)
            for e in range(3)] for k, pair in enumerate(pairs)]
    kernel = [[(target[i]-f[i] if i == j else 0) +
               sum(jac[i][e]*h[e]*jac[j][e] for e in range(3))
               for j in range(3)] for i in range(3)]
    t = h[0]*h[1]*h[2]/total**2
    for i in range(3):
        for j in range(3):
            defect = (target[i] if i == j else 0)-kernel[i][j]
            assert defect == 3*f[i]*f[j]/total+t*(2*F(i == j)-1)
    return kernel, sum(target)+sum(h)-sum(f)


def inverse(mat):
    a = [list(row)+[F(i == j) for j in range(3)]
         for i, row in enumerate(mat)]
    for i in range(3):
        pivot = a[i][i]
        a[i] = [x/pivot for x in a[i]]
        for j in range(3):
            if j != i:
                factor = a[j][i]
                a[j] = [a[j][k]-factor*a[i][k] for k in range(6)]
    return [row[3:] for row in a]


def sqrt_bounds(x, digits):
    scale = 10**digits
    n = isqrt((x.numerator*scale**2)//x.denominator)
    lo, hi = F(n, scale), F(n+1, scale)
    assert lo**2 <= x < hi**2
    return lo, hi


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--delta", required=True)
    p.add_argument("--weak-ratio", required=True)
    p.add_argument("--strong-value", required=True)
    p.add_argument("--digits", required=True, type=int)
    a = p.parse_args()
    delta = F(a.delta)
    reference = [delta**2/(1+2*delta),
                 delta/(1+2*delta), delta/(1+2*delta)]
    target = [2*x for x in reference]
    ref_k, _ = matrix(reference, target)
    vec = [[row[i] for row in ref_k] for i in (1, 2)]
    vec.append([vec[0][i]-vec[1][i] for i in range(3)])
    point = [F(a.weak_ratio)*target[0],
             F(a.strong_value), F(a.strong_value)]
    assert all(0 < point[i] < target[i] for i in range(3))
    k, mass = matrix(point, target)
    inv = inverse(k)
    low = high = F(0)
    squares = []
    for v in vec:
        u = [sum(inv[i][j]*v[j] for j in range(3)) for i in range(3)]
        square = sum(x*x for x in u)
        squares.append(str(square))
        lo, hi = sqrt_bounds(square, a.digits)
        low += lo
        high += hi
    phi = sum(reference)
    canonical_min = 2*(1+2*delta+2*phi)
    r_edge = delta/(2*(1+delta))
    edge_cap = (target[0]+4*target[1]+3*target[1]*r_edge
                +target[1]/r_edge)
    out = {"delta": str(delta), "f": list(map(str, point)),
           "C0": list(map(str, target)), "mass": str(mass),
           "canonical_budget_lower": str(canonical_min),
           "feasible_at_canonical_lower": mass <= canonical_min,
           "edge_sufficient_budget_cap": str(edge_cap),
           "squared_norms": squares,
           "ell_lower": str(low), "ell_upper": str(high),
           "method": "Fraction arithmetic; integer-square-root enclosures",
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
