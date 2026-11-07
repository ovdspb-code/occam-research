"""Directed-rounding interval certificate on the whole d12=0 face.
The square parametrizes f12=C01,f13=C02*s,f23=C02*k*s,0<=k,s<=1.
Exchange of terminals 1,2 covers the other half. No material cap imposed.
Configuration is supplied by CLI; failure to certify is not a counterexample.
"""
import argparse, hashlib, heapq, json, math, time
from fractions import Fraction as F
from pathlib import Path

def dn(x): return math.nextafter(x, -math.inf)
def up(x): return math.nextafter(x, math.inf)
class I:
    __slots__=("a","b")
    def __init__(self,a,b=None): self.a=float(a); self.b=float(a if b is None else b)
    @staticmethod
    def rat(q):
        q=F(q); f=float(q)
        return I(dn(f),up(f))
    def __add__(self,o):
        o=iv(o); return I(dn(self.a+o.a),up(self.b+o.b))
    __radd__=__add__
    def __neg__(self): return I(-self.b,-self.a)
    def __sub__(self,o): return self+-iv(o)
    def __rsub__(self,o): return iv(o)+-self
    def __mul__(self,o):
        o=iv(o); v=[self.a*o.a,self.a*o.b,self.b*o.a,self.b*o.b]
        return I(dn(min(v)),up(max(v)))
    __rmul__=__mul__
    def __truediv__(self,o):
        o=iv(o)
        if o.a<=0<=o.b: raise ZeroDivisionError
        return self*I(dn(1/o.b),up(1/o.a))
    def square(self):
        lo=0 if self.a<=0<=self.b else dn(min(self.a*self.a,self.b*self.b))
        return I(max(0,lo),up(max(self.a*self.a,self.b*self.b)))
    def sqrt(self): return I(max(0,dn(math.sqrt(max(0,self.a)))),up(math.sqrt(max(0,self.b))))
def iv(x): return x if isinstance(x,I) else I(x)

def ref(delta):
    h=[delta,delta,F(1)]; S=sum(h); pairs=[(0,1),(0,2),(1,2)]
    f=[h[i]*h[j]/S for i,j in pairs]
    J=[[(int(e==i)*h[j]+int(e==j)*h[i])/S-h[i]*h[j]/S**2 for e in range(3)] for i,j in pairs]
    K=[[sum(J[i][e]*h[e]*J[j][e] for e in range(3))+(f[i] if i==j else 0) for j in range(3)] for i in range(3)]
    return [2*t for t in f],[[K[i][1] for i in range(3)],[K[i][2] for i in range(3)]]

def matrix(k,s,small,big):
    R=small*(1+k)+big*k*s
    R2=R.square()
    a=small.square()*(small*(1-k+k.square())+big*s*(k+k.square()))/R2
    b=-small*big*k*s*(2*small-small*k-big*k*s)/R2
    c=small*big*k*s*(small-2*small*k+big*k*s)/R2
    d=big*(1-s)+big*s*(small.square()*(1+k)+small*big*s*(k.square()-k)+big.square()*k.square()*s.square())/R2
    e=small*big*k*s*(small*(1+k)-2*big*k*s)/R2
    f=big*(1-k*s)+k.square()*big*s*(small.square()*(1+k)+small*big*s*(1-k)+big.square()*k*s.square())/R2
    return a,b,c,d,e,f

def length(box,small,big,vs):
    k=I(box[0],box[1]); s=I(box[2],box[3])
    a,b,c,d,e,f=matrix(k,s,small,big)
    aa=d*f-e.square(); ab=c*e-b*f; ac=b*e-c*d
    dd=a*f-c.square(); de=b*c-a*e; ff=a*d-b.square()
    det=a*aa+b*ab+c*ac
    if det.a<=0: return -math.inf
    inv=[[aa,ab,ac],[ab,dd,de],[ac,de,ff]]
    total=I(0)
    for v in vs:
        z=[sum((row[j]*v[j] for j in range(3)),I(0))/det for row in inv]
        total+=sum((x.square() for x in z),I(0)).sqrt()
    return total.a

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--delta",required=True); ap.add_argument("--max-boxes",type=int,required=True)
    ap.add_argument("--wall-seconds",type=float,required=True); ap.add_argument("--output",required=True)
    args=ap.parse_args(); delta=F(args.delta); C,vs=ref(delta)
    assert C[1]==C[2] and 0<delta<1
    vs=vs+[[vs[0][i]-vs[1][i] for i in range(3)]]
    vs=[[I.rat(x) for x in v] for v in vs]
    small,big=I.rat(C[0]),I.rat(C[1])
    target=up(2+up(math.sqrt(2)))
    heap=[(-math.inf,0,(0.,1.,0.,1.))]; count=0; accepted=0; lowest=math.inf
    start=time.monotonic(); serial=0
    while heap and count<args.max_boxes and time.monotonic()-start<args.wall_seconds:
        _,_,box=heapq.heappop(heap); count+=1
        try: lo=length(box,small,big,vs)
        except (ZeroDivisionError,OverflowError,ValueError): lo=-math.inf
        if lo>target:
            accepted+=1; lowest=min(lowest,lo); continue
        k0,k1,s0,s1=box
        if k1-k0>=s1-s0:
            mid=(k0+k1)/2; children=[(k0,mid,s0,s1),(mid,k1,s0,s1)]
        else:
            mid=(s0+s1)/2; children=[(k0,k1,s0,mid),(k0,k1,mid,s1)]
        for ch in children:
            serial+=1;heapq.heappush(heap,(lo,serial,ch))
    out={"delta":str(delta),"face":"d12=0","domain":"all material budgets; positive-star closure","target_upper":target,
         "certified":not heap,"processed":count,"accepted":accepted,"pending":len(heap),
         "smallest_accepted_lower":lowest if math.isfinite(lowest) else None,
         "elapsed_seconds":time.monotonic()-start,
         "pending_worst":heap[0][2] if heap else None,
         "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path(args.output).write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
if __name__=="__main__":main()

