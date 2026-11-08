"""Exact rational bounds for the two global direct-only certificates.
No local optimization, interval search, or physical-state subdivision.
"""
from fractions import Fraction as F
from math import isqrt
from pathlib import Path
import json

A,B=F(1,5100),F(1,51)
K=[[F(707,7074720),F(11,117912),F(11,117912)],
   [F(11,117912),F(3401,176868),F(-11,58956)],
   [F(11,117912),F(-11,58956),F(3401,176868)]]
D=[A,B,B]
SCALE=10**10

def root_bounds(q):
    n=isqrt(q.numerator*SCALE*SCALE//q.denominator)
    lo,hi=F(n,SCALE),F(n+1,SCALE)
    assert lo*lo<=q and hi*hi>=q
    return lo,hi

def supporting(theta):
    a1=[K[i][1]+K[i][2] for i in range(3)]
    a2=[theta*K[i][0] for i in range(3)]
    ws=[a1,[a2[i]-a1[i] for i in range(3)],[-x for x in a2]]
    Z=[[[F(0),F(0)] for j in range(3)] for i in range(3)]
    for w in ws:
        y=[w[i]/D[i] for i in range(3)]
        nl,nh=root_bounds(sum(t*t for t in y))
        for i in range(3):
            for j in range(3):
                coef=(w[i]*y[j]+y[i]*w[j])/2
                terms=(coef/nl,coef/nh)
                Z[i][j][0]+=min(terms)
                Z[i][j][1]+=max(terms)
    return Z

def matvec(m,x):
    return [sum(m[i][j]*x[j] for j in range(3)) for i in range(3)]

def inverse(m):
    r=[[F(0) for j in range(3)] for i in range(3)]
    det=sum(m[0][j]*(m[1][(j+1)%3]*m[2][(j+2)%3]-
                    m[1][(j+2)%3]*m[2][(j+1)%3]) for j in range(3))
    for i in range(3):
        for j in range(3):
            r[i][j]=(m[(j+1)%3][(i+1)%3]*m[(j+2)%3][(i+2)%3]-
                     m[(j+1)%3][(i+2)%3]*m[(j+2)%3][(i+1)%3])/det
    return r

def witness(theta,h):
    a,b,c=h;m=a+b+c;f=[a*b/m,a*c/m,b*c/m]
    Q=f[0]*f[1]+f[0]*f[2]+f[1]*f[2];t=f[0]*f[1]*f[2]/Q
    k=[[(D[i] if i==j else 0)-t*(2*(i==j)-1)-3*t*f[i]*f[j]/Q
        for j in range(3)] for i in range(3)]
    ki=inverse(k);a1=[K[i][1]+K[i][2] for i in range(3)]
    a2=[theta*K[i][0] for i in range(3)]
    ws=[a1,[a2[i]-a1[i] for i in range(3)],[-x for x in a2]]
    upper=F(0);direct_lower=F(0)
    for w in ws:
        y=matvec(ki,w);upper+=root_bounds(sum(x*x for x in y))[1]
        y=[w[i]/D[i] for i in range(3)]
        direct_lower+=root_bounds(sum(x*x for x in y))[0]
    material=sum(D)+m-sum(f)
    assert all(f[i]<D[i] for i in range(3))
    assert material<F(181901,85000) and upper<direct_lower
    return {'theta':str(theta),'h':[str(x) for x in h],
            'material':str(material),'length_upper':str(upper),
            'direct_length_lower':str(direct_lower)}

def interval_json(z):
    return {'lower':str(z[0]),'upper':str(z[1]),
            'decimal_lower':float(z[0]),'decimal_upper':float(z[1])}

def main():
    out={'label':'EXACT FINITE ARITHMETIC CHECK, NOT AN OPTIMIZER',
         'sqrt_scale':SCALE,'certificates':[]}
    for theta in [2,4]:
        Z=supporting(theta);alpha,beta,gamma=Z[0][0],Z[1][1],Z[0][1]
        assert Z[0][1]==Z[0][2] and Z[1][1]==Z[1][2]==Z[2][2]
        item={'theta':theta,'alpha':interval_json(alpha),
              'beta':interval_json(beta),'gamma':interval_json(gamma)}
        if theta==2:
            kappa=2*A/(B-6*A)
            lower=alpha[0]-2*kappa*gamma[1]
            assert gamma[0]>0 and beta[0]>0 and lower>F(8,100000)
            item['alpha_minus_2kappa_gamma_lower']=str(lower)
            item['proved_simple_bound']='alpha-2*kappa*gamma > 8/100000'
        else:
            cross=max(abs(gamma[0]),abs(gamma[1]))
            determinant_lower=alpha[0]*beta[0]-cross*cross
            assert alpha[0]>F(63,100000) and beta[0]>F(21,1000)
            assert cross<F(3,10000) and determinant_lower>0
            item['determinant_lower']=str(determinant_lower)
            item['proved_simple_bounds']='alpha>63/100000,beta>21/1000,abs(gamma)<3/10000'
        out['certificates'].append(item)
    out['small_theta_witnesses']=[]
    for theta in [F(1,4),F(1,2),F(1)]:
        Z=supporting(theta)
        assert Z[0][0][0]>0 and Z[1][1][0]>0 and Z[0][1][0]>0
        h=[F(1,100),F(1,100),F(1)] if theta<1 else [F(17,2000),F(17,2000),F(21,10)]
        out['small_theta_witnesses'].append(witness(theta,h))
    Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':
    main()
