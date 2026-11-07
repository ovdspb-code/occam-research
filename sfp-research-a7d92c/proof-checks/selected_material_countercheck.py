"""Exact independent check of a failed uniform SPD sufficient condition."""
import argparse
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
import sympy as s
from direct_face_12_certificate import ref
from strong_face_exact_evidence import sqrt_bounds


def main():
    p = argparse.ArgumentParser()
    for name in ('delta', 'x', 'center', 'budget', 'target', 'output'):
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    C, vs = ref(F(a.delta))
    x, c = s.Rational(a.x), s.Rational(a.center)
    f = s.Matrix([x, c+x, c-x])
    Q = f[0]*f[1]+f[0]*f[2]+f[1]*f[2]
    t = s.prod(f)/Q
    K = s.diag(*map(s.Rational, C))-t*(2*s.eye(3)-s.ones(3))-3*t/Q*f*f.T
    W = s.diag(*[(Q-f[i]**2)/(f[(i+1)%3]*f[(i+2)%3]) for i in range(3)])
    mass = sum(C)+sum(f)+sum(f[i]*f[j]/f[k] for i,j,k in [(0,1,2),(0,2,1),(1,2,0)])
    assert all(0 < f[i] < C[i] for i in range(3))
    assert mass < s.Rational(a.budget)
    assert W[1,1] < 0 and (K*W+W*K)[1,1] < 0
    vs.append([vs[0][i]-vs[1][i] for i in range(3)])
    lo = hi = F(0)
    forms = []
    for v in vs:
        u = K.inv()*s.Matrix(v)
        l,h = sqrt_bounds(F((u.T*u)[0]), 12)
        lo += l; hi += h
        forms.append((u.T*K.inv()*W*u)[0])
    assert hi < F(a.target)
    assert all(q > 0 for q in forms)
    out = dict(scope='Counterexample to uniform SPD only; no proof of saturation',
               parameters=vars(a), mass=str(mass), W2=str(W[1,1]),
               ell_bounds=[str(lo),str(hi)], specific_forms_positive=True,
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__ == '__main__':
    main()
