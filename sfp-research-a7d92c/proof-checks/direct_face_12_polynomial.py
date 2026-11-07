"""Exact symbolic reduction followed by directed-rounding face certification."""
import argparse, hashlib, heapq, json, math, time
from pathlib import Path
from fractions import Fraction
import sympy as sy
from direct_face_12_certificate import I,ref

def coefficients(expr,k,t):
    p=sy.Poly(expr,k); out=[]
    for ck in p.all_coeffs():
        out.append([I.rat(str(x)) for x in sy.Poly(ck,t).all_coeffs()])
    return out
def ev(co,k,t):
    out=I(0)
    for row in co:
        z=I(0)
        for x in row:z=z*t+x
        out=out*k+z
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--delta",required=True);ap.add_argument("--max-boxes",type=int,required=True)
    ap.add_argument("--wall-seconds",type=float,required=True);ap.add_argument("--output",required=True)
    args=ap.parse_args(); C,vs=ref(Fraction(args.delta))
    k,t=sy.symbols("k t");F,D=map(lambda x:sy.Rational(str(x)),C[:2]);R=F*(1+k)+D*k*t
    a=F**2*(F*(1-k+k*k)+D*t*(k+k*k))
    b=-F*D*k*t*(2*F-F*k-D*k*t)
    c=F*D*k*t*(F-2*F*k+D*k*t)
    d=D*(1-t)*R**2+D*t*(F**2*(1+k)+F*D*t*(k*k-k)+D**2*k*k*t*t)
    e=F*D*k*t*(F*(1+k)-2*D*k*t)
    f=D*(1-k*t)*R**2+k*k*D*t*(F**2*(1+k)+F*D*t*(1-k)+D**2*k*t*t)
    K=sy.Matrix([[a,b,c],[b,d,e],[c,e,f]])
    adj=K.adjugate(); det=sy.factor(K.det())
    vs=vs+[[vs[0][i]-vs[1][i] for i in range(3)]]
    polys=[]
    for v in vs:
        u=adj*sy.Matrix([sy.Rational(str(x)) for x in v])*R**2/det
        group=[]
        for x in u:
            num,den=sy.fraction(sy.cancel(x))
            group.append((coefficients(num,k,t),coefficients(den,k,t)))
        polys.append(group)
    def lower(box):
        ki=I(box[0],box[1]);ti=I(box[2],box[3]);total=I(0)
        for group in polys:
            norm=I(0)
            for num,den in group:
                norm+=(ev(num,ki,ti)/ev(den,ki,ti)).square()
            total+=norm.sqrt()
        return total.a
    target=math.nextafter(2+math.nextafter(math.sqrt(2),math.inf),math.inf)
    heap=[(-math.inf,0,(0.,1.,0.,1.))];count=accepted=serial=0;lowest=math.inf;start=time.monotonic()
    while heap and count<args.max_boxes and time.monotonic()-start<args.wall_seconds:
        _,_,box=heapq.heappop(heap);count+=1
        try:lo=lower(box)
        except(ZeroDivisionError,ValueError,OverflowError):lo=-math.inf
        if lo>target:accepted+=1;lowest=min(lowest,lo);continue
        k0,k1,s0,s1=box
        if k1-k0>=s1-s0:
            m=(k0+k1)/2;children=[(k0,m,s0,s1),(m,k1,s0,s1)]
        else:
            m=(s0+s1)/2;children=[(k0,k1,s0,m),(k0,k1,m,s1)]
        for ch in children:serial+=1;heapq.heappush(heap,(lo,serial,ch))
    out={"delta":args.delta,"face":"d12=0","method":"exact rational cancellation plus outward interval Horner",
         "certified":not heap,"processed":count,"accepted":accepted,"pending":len(heap),"target_upper":target,
         "smallest_accepted_lower":lowest if math.isfinite(lowest) else None,"elapsed_seconds":time.monotonic()-start,
         "pending_worst":heap[0][2] if heap else None,"script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         "interval_library_sha256":hashlib.sha256(Path(__file__).with_name("direct_face_12_certificate.py").read_bytes()).hexdigest()}
    Path(args.output).write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,indent=2))
if __name__=="__main__":main()

