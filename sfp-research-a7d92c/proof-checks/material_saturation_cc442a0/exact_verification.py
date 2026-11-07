"""Independent exact algebra for the saturation proof (no original SFP imports)."""
import sympy as s
from pathlib import Path
import json
out={}
a,b,c=s.symbols('a b c',positive=True);h=s.Matrix([a,b,c]);m=a+b+c
f=s.Matrix([a*b,a*c,b*c])/m;J=f.jacobian(h)
D=s.diag(s.Rational(1,5100),s.Rational(1,51),s.Rational(1,51));C=s.Matrix(list(D.diagonal()))
t=a*b*c/m**2
Kphysical=D-s.diag(*f)+J*s.diag(a,b,c)*J.T
Kcompact=D-2*t*s.eye(3)+t*s.ones(3)-3*f*f.T/m
out['physical_K_equals_compact']=[s.factor(Kphysical[i,j]-Kcompact[i,j])==0 for i in range(3) for j in range(i,3)]
out['det_Df']=str(s.factor(J.det()))
x,y,z=s.symbols('x y z',positive=True);ff=s.Matrix([x,y,z]);Q=x*y+x*z+y*z;tt=x*y*z/Q
KK=D-2*tt*s.eye(3)+tt*s.ones(3)-3*tt*ff*ff.T/Q
checks=[]
for k in range(3):
 dq=C[k]*sum(ff[j] for j in range(3) if j!=k);dt=tt*(C[k]/ff[k]-dq/Q)
 df=s.zeros(3,1);df[k]=C[k]
 manual=-2*dt*s.eye(3)+dt*s.ones(3)-3*(dt/Q-tt*dq/Q**2)*ff*ff.T-3*tt/Q*(df*ff.T+ff*df.T)
 checks += [s.factor(manual[i,j]-C[k]*s.diff(KK[i,j],ff[k]))==0 for i in range(3) for j in range(i,3)]
out['coordinate_derivatives_exact']=all(checks)
T,b0,b1=s.symbols('T b0 b1');bs=[b0,b1,-b0-b1];ps=[(T-v)/(3*T) for v in bs]
wchecks=[]
for i in range(3):
 j,k=[v for v in range(3) if v!=i]
 kii=C[i]-T-(T-bs[j])*(T-bs[k])/(T-bs[i]);wi=(ps[i]-ps[j]*ps[k])/ps[i]**2
 wchecks.append(s.factor(s.diff(kii,T)+wi)==0)
out['fixed_offdiagonal_derivative_exact']=all(wchecks)
L=s.Rational(6825559,2000000);tm=s.Rational(19673,4607252325)
out['competitive_t_floor_exact']=s.Rational(4,9)*C[0]*(s.Rational(179,50)/L-1)==tm
ref={a:s.Rational(1,100),b:s.Rational(1,100),c:1};Kr=Kphysical.subs(ref);v1=Kr[:,1];v2=Kr[:,2]
vv=[v1,v2,v1-v2];dd=[D.inv()*v for v in vv];out['ell_direct_gt_179_over_50']=bool(sum(s.sqrt((v.T*v)[0]) for v in dd)>s.Rational(179,50))
fc=s.Matrix([s.Rational(29603,318750000),s.Rational(17807587,1275000000),s.Rational(5856921,425000000)])
Kc=KK.subs(dict(zip(ff,fc)));qc=Q.subs(dict(zip(ff,fc)));W=s.diag(*[(qc-fc[i]**2)/(fc[(i+1)%3]*fc[(i+2)%3]) for i in range(3)])
out['counterexample_W2']=str(W[1,1]);out['counterexample_Jordan_diagonal_negative']=bool(2*Kc[1,1]*W[1,1]<0)
u=[Kc.inv()*v for v in vv];out['counterexample_three_forms_positive']=[bool((v.T*Kc.inv()*W*v)[0]>0) for v in u]
# Reference relation used by the all-control material bound.
alpha=s.Rational(10506,10205);beta=s.Rational(408,10205)
out['reference_C_decomposition']=list(C-alpha*(v1+v2)-beta*Kr[:,0])==[0,0,0]
out['new_ODE']=False;out['new_global_stationarity_result_is_interval_not_symbolic']=True
print(json.dumps(out,indent=2));Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n')
