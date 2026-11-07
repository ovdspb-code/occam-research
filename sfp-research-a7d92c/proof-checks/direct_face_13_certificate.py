"""Uniform certificate on d13=0 under a CLI material ceiling.
The d23 face follows by the fixed terminal 1<->2 symmetry.
"""
import argparse,hashlib,heapq,json,math,time
from pathlib import Path
from fractions import Fraction
import sympy as sy
from direct_face_12_certificate import I,ref
from direct_face_12_polynomial import coefficients,ev

def main():
 ap=argparse.ArgumentParser()
 for n in ("delta","budget","target","output"):ap.add_argument("--"+n,required=True)
 ap.add_argument("--max-boxes",type=int,required=True);ap.add_argument("--wall-seconds",type=float,required=True)
 args=ap.parse_args(); C0,vs=ref(Fraction(args.delta)); CB=[sy.Rational(str(c)) for c in C0]
 B=sy.Rational(args.budget);target=I.rat(args.target).b;F=CB[1];A=B-sum(CB)
 assert A>0 and CB[1]==CB[2]
 r,t,s=sy.symbols("r t s");R=F*(1+r)+r*t
 a=r*r*t*(F*F*(1+r)+F*t*(1-r)+r*t*t)
 b=-r*F*t*(2*r*F-r*t-F)
 c=r*F*t*(r*F-2*r*t+F)
 d=F*F*(F*(r*r-r+1)+t*(r*r+r))
 e=r*F*t*(r*F+r*t-2*F)
 f=t*(F*F*(r+1)+F*t*(r*r-r)+r*r*t*t)
 K=sy.Matrix([[a+(CB[0]-r*t)*R**2,b,c],[b,d,e],[c,e,f+(CB[2]-t)*R**2]])
 adj=K.adjugate();det=sy.factor(K.det())
 vs=vs+[[vs[0][i]-vs[1][i] for i in range(3)]]
 uv=[adj*sy.Matrix([sy.Rational(str(z)) for z in v])*R**2/det for v in vs]
 patches=[]
 for texpr in (CB[2]*s,CB[0]*s/r):
  polys=[]
  for group in uv:
   out=[]
   for u in group:
    n,q=sy.fraction(sy.cancel(u.subs(t,texpr)));out.append((coefficients(n,r,s),coefficients(q,r,s)))
   polys.append(out)
  patches.append(polys)
 rlo=I.rat(str(F/A)).a;rhi=I.rat(str(A/F)).b;cut=I.rat(str(CB[0]/CB[2]))
 heap=[];serial=0
 if rlo<cut.b:heap.append((-math.inf,serial,0,(rlo,min(rhi,cut.b),0.,1.)));serial+=1
 if rhi>cut.a:heap.append((-math.inf,serial,1,(max(rlo,cut.a),rhi,0.,1.)));serial+=1
 heapq.heapify(heap);Biv=I.rat(args.budget);Fiv=I.rat(str(F));sumC=I.rat(str(sum(CB)));small=I.rat(str(CB[0]));big=I.rat(str(CB[2]))
 def evaluate(p,box):
  ri=I(box[0],box[1]);si=I(box[2],box[3]);ti=big*si if p==0 else small*si/ri
  mass=sumC+Fiv*(1+ri+I(1)/ri)+(ri+1)*ti+ri*ti.square()/Fiv
  if mass.a>Biv.b:return math.inf
  total=I(0)
  for group in patches[p]:
   norm=I(0)
   for n,q in group:norm+=(ev(n,ri,si)/ev(q,ri,si)).square()
   total+=norm.sqrt()
  return total.a
 count=accepted=pruned=0;lowest=math.inf;start=time.monotonic()
 while heap and count<args.max_boxes and time.monotonic()-start<args.wall_seconds:
  _,_,p,box=heapq.heappop(heap);count+=1
  try:lo=evaluate(p,box)
  except(ZeroDivisionError,ValueError,OverflowError):lo=-math.inf
  if lo>target:
   if lo==math.inf:pruned+=1
   else:accepted+=1;lowest=min(lowest,lo)
   continue
  r0,r1,s0,s1=box
  if math.log(r1/r0)>=s1-s0:
   mid=math.sqrt(r0*r1);children=[(r0,mid,s0,s1),(mid,r1,s0,s1)]
  else:
   mid=(s0+s1)/2;children=[(r0,r1,s0,mid),(r0,r1,mid,s1)]
  for ch in children:serial+=1;heapq.heappush(heap,(lo,serial,p,ch))
 out={"delta":args.delta,"budget_upper":args.budget,"face":"d13=0 and d23=0 by symmetry","target":args.target,"target_upper":target,
      "certified":not heap,"processed":count,"accepted":accepted,"material_pruned":pruned,"pending":len(heap),
      "smallest_accepted_lower":lowest if math.isfinite(lowest) else None,"elapsed_seconds":time.monotonic()-start,
      "pending_worst":heap[0][2:] if heap else None,
      "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 Path(args.output).write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,indent=2))
if __name__=="__main__":main()

