
// ===== GKSL ENGINE (N=8) =====
const N=8, W=[[0,1,0,0,0,0,0,0],[1,0,1,0,0,0,0,0],[0,1,0,1,0,0,0,0],[0,0,1,0,1,0,0,0],[0,0,0,1,0,1,0,0],[0,0,0,0,1,0,1,0],[0,0,0,0,0,1,0,1],[0,0,0,0,0,0,1,0]];
const isTgt=new Uint8Array(N); isTgt[7]=1;
const ci=(i,j)=>2*(i*N+j);

function newRho(){const r=new Float64Array(2*N*N);r[ci(0,0)]=1;return r}

const H=new Float64Array(N*N);
(function(){for(let i=0;i<N;i++){let d=0;for(let j=0;j<N;j++){if(W[i][j]){H[i*N+j]=W[i][j];d+=W[i][j]}}H[i*N+i]=-d}})();

function lind(rho,k,g,out){
  for(let i=0;i<N;i++)for(let j=0;j<N;j++){
    const idx=ci(i,j);let hr=0,hi=0,pr=0,pi=0;
    for(let m=0;m<N;m++){const a=H[i*N+m];if(a){const c=ci(m,j);hr+=a*rho[c];hi+=a*rho[c+1]}const b=H[m*N+j];if(b){const c=ci(i,m);pr+=rho[c]*b;pi+=rho[c+1]*b}}
    let dr=hi-pi,di=-(hr-pr);
    if(i!==j){dr-=k*rho[idx];di-=k*rho[idx+1]}
    const s=g*.5*(isTgt[i]+isTgt[j]);if(s){dr-=s*rho[idx];di-=s*rho[idx+1]}
    out[idx]=dr;out[idx+1]=di;
  }
}

const L=2*N*N,k1=new Float64Array(L),k2=new Float64Array(L),k3=new Float64Array(L),k4=new Float64Array(L),tmp=new Float64Array(L);
function rk4(rho,dt,k,g){
  lind(rho,k,g,k1);for(let i=0;i<L;i++)tmp[i]=rho[i]+.5*dt*k1[i];
  lind(tmp,k,g,k2);for(let i=0;i<L;i++)tmp[i]=rho[i]+.5*dt*k2[i];
  lind(tmp,k,g,k3);for(let i=0;i<L;i++)tmp[i]=rho[i]+dt*k3[i];
  lind(tmp,k,g,k4);for(let i=0;i<L;i++)rho[i]+=(dt/6)*(k1[i]+2*k2[i]+2*k3[i]+k4[i]);
}

let rho, simT=0, playing=false, animId=null;
const dt=.01, spf=10;
const getK=()=>Math.pow(10,+document.getElementById('kSlider').value);
const getG=()=>+document.getElementById('gSlider').value;

function resetSim(){rho=newRho();simT=0;drawSim();updInfo()}
function togglePlay(){playing=!playing;document.getElementById('playBtn').textContent=playing?'Pause':'Play';if(playing)anim();else{cancelAnimationFrame(animId);animId=null}}
function anim(){if(!playing)return;for(let s=0;s<spf;s++){rk4(rho,dt,getK(),getG());simT+=dt}drawSim();updInfo();animId=requestAnimationFrame(anim)}
function updInfo(){let pt=rho[ci(7,7)],ps=rho[ci(0,0)];document.getElementById('info').textContent=`t=${simT.toFixed(2)} | P_target=${pt.toFixed(4)} | P_source=${ps.toFixed(4)}`}

const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();

function drawSim(){
  const c=document.getElementById('simCanvas'),ctx=c.getContext('2d'),dpr=devicePixelRatio||1;
  const CW=c.clientWidth,CH=c.clientHeight;c.width=CW*dpr;c.height=CH*dpr;ctx.scale(dpr,dpr);ctx.clearRect(0,0,CW,CH);
  const cS=css('--c-src'),cT=css('--c-tgt'),cI=css('--c-int'),brd=css('--border'),txt=css('--text-3'),txM=css('--text');
  const pad=60,gap=(CW-2*pad)/(N-1),cy=CH*.38;
  // Edges
  ctx.strokeStyle=brd+'88';ctx.lineWidth=2;
  for(let i=0;i<N-1;i++){ctx.beginPath();ctx.moveTo(pad+i*gap,cy);ctx.lineTo(pad+(i+1)*gap,cy);ctx.stroke()}
  // Nodes + bars
  for(let i=0;i<N;i++){
    const x=pad+i*gap,pop=Math.max(0,rho[ci(i,i)]),r=8+pop*40,col=i===0?cS:i===7?cT:cI;
    ctx.beginPath();ctx.arc(x,cy,Math.min(r,35),0,Math.PI*2);ctx.fillStyle=col;ctx.globalAlpha=.3+pop*3;ctx.fill();ctx.globalAlpha=1;ctx.lineWidth=2;ctx.strokeStyle=col;ctx.stroke();
    ctx.fillStyle=txt;ctx.font='600 11px '+css('--font-mono');ctx.textAlign='center';ctx.fillText(i+'',x,cy+48);
    // Bar
    const barH=Math.min(pop*150,80);ctx.fillStyle=col;ctx.globalAlpha=.5;ctx.fillRect(x-10,CH-20-barH,20,barH);ctx.globalAlpha=1;
    if(pop>.005){ctx.fillStyle=txM;ctx.font='600 9px '+css('--font-mono');ctx.fillText(pop.toFixed(3),x,cy-Math.min(r,35)-6)}
  }
}

document.getElementById('kSlider').addEventListener('input',()=>{document.getElementById('kVal').textContent=getK().toFixed(2)});
document.getElementById('gSlider').addEventListener('input',()=>{document.getElementById('gVal').textContent=getG().toFixed(2)});

// ===== STATIC CHARTS =====
const GA=[{k:.01,v:.015},{k:.025,v:.023},{k:.063,v:.042},{k:.1,v:.06},{k:.16,v:.074},{k:.25,v:.08},{k:.4,v:.083},{k:.63,v:.082},{k:1,v:.078},{k:1.6,v:.071},{k:2.5,v:.061},{k:4,v:.049},{k:6.3,v:.038},{k:10,v:.027},{k:25,v:.013},{k:63,v:.005},{k:100,v:.003}];
const TR=[{n:.01,t:.18,m:.68,f:.43},{n:.05,t:.43,m:.66,f:.55},{n:.1,t:.73,m:.54,f:.63},{n:.2,t:.93,m:.36,f:.64},{n:.5,t:1,m:.29,f:.64},{n:1,t:.94,m:.30,f:.62},{n:2,t:.79,m:.29,f:.54},{n:5,t:.52,m:.29,f:.41},{n:10,t:.33,m:.29,f:.31}];
const CX=[{x:.01,r:.57,l:.28,s:2.04},{x:.05,r:.56,l:.29,s:1.93},{x:.1,r:.48,l:.40,s:1.20},{x:.2,r:.32,l:.60,s:.53},{x:.5,r:.27,l:.66,s:.41},{x:1,r:.27,l:.66,s:.42},{x:2,r:.27,l:.66,s:.41},{x:5,r:.27,l:.66,s:.41},{x:10,r:.27,l:.67,s:.40}];
const EN=[{t:.5,e:3.2},{t:1,e:2.8},{t:2,e:2.1},{t:5,e:1.4},{t:10,e:.9},{t:20,e:.6},{t:50,e:.35},{t:100,e:.2},{t:200,e:.12},{t:500,e:.06}];

function lc(id,data,xk,yks,xLab,yLab,opts={}){
  const c=document.getElementById(id),ctx=c.getContext('2d'),dpr=devicePixelRatio||1;
  const CW=c.clientWidth,CH=c.clientHeight;c.width=CW*dpr;c.height=CH*dpr;ctx.scale(dpr,dpr);ctx.clearRect(0,0,CW,CH);
  const ml=50,mr=10,mt=10,mb=30,pw=CW-ml-mr,ph=CH-mt-mb;
  const aY=[];data.forEach(d=>yks.forEach(y=>{if(d[y.k]!=null)aY.push(d[y.k])}));
  const yMn=opts.yMin??Math.min(...aY)*.9, yMx=opts.yMax??Math.max(...aY)*1.08;
  const lg=opts.logX, xVs=data.map(d=>lg?Math.log10(d[xk]):d[xk]);
  const xMn=Math.min(...xVs),xMx=Math.max(...xVs);
  const tX=v=>ml+((lg?Math.log10(v):v)-xMn)/(xMx-xMn)*pw;
  const tY=v=>mt+(1-(v-yMn)/(yMx-yMn))*ph;
  // grid
  ctx.strokeStyle=css('--border-light');ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const y=mt+ph*i/4;ctx.beginPath();ctx.moveTo(ml,y);ctx.lineTo(ml+pw,y);ctx.stroke()}
  // peak
  if(opts.peak){let bv=-Infinity,bd;const pk=yks[0].k;data.forEach(d=>{if(d[pk]>bv){bv=d[pk];bd=d}});if(bd){const px=tX(bd[xk]),py=tY(bv);ctx.beginPath();ctx.arc(px,py,6,0,Math.PI*2);ctx.strokeStyle=yks[0].c;ctx.lineWidth=2;ctx.stroke();ctx.fillStyle=css('--text');ctx.font='600 9px '+css('--font-mono');ctx.textAlign='center';ctx.fillText('k*='+bd[xk],px,py-10)}}
  // lines
  yks.forEach(yk=>{ctx.strokeStyle=yk.c;ctx.lineWidth=2;ctx.beginPath();let f=1;data.forEach(d=>{if(d[yk.k]==null)return;const x=tX(d[xk]),y=tY(d[yk.k]);f?(ctx.moveTo(x,y),f=0):ctx.lineTo(x,y)});ctx.stroke();
  data.forEach(d=>{if(d[yk.k]==null)return;ctx.beginPath();ctx.arc(tX(d[xk]),tY(d[yk.k]),3,0,Math.PI*2);ctx.fillStyle=yk.c;ctx.fill()})});
  // labels
  ctx.fillStyle=css('--text-3');ctx.font='500 10px '+css('--font-body');ctx.textAlign='center';ctx.fillText(xLab,ml+pw/2,CH-4);
  ctx.save();ctx.translate(10,mt+ph/2);ctx.rotate(-Math.PI/2);ctx.fillText(yLab,0,0);ctx.restore();
  ctx.font='9px '+css('--font-mono');ctx.textAlign='right';
  for(let i=0;i<=4;i++){const v=yMn+(yMx-yMn)*i/4;ctx.fillText(v.toFixed(2),ml-4,mt+ph*(1-i/4)+3)}
}

function drawCharts(){
  const c0=css('--c0'),c1=css('--c1'),c2=css('--c2');
  lc('cA',GA,'k',[{k:'v',c:c0}],'kappa','Gap',{logX:1,yMin:0,yMax:.1,peak:1});
  lc('cB',TR,'n',[{k:'t',c:c0},{k:'m',c:c1},{k:'f',c:c2}],'noise','score',{logX:1,yMin:0,yMax:1.1});
  lc('cC',CX,'x',[{k:'r',c:c0},{k:'l',c:c1},{k:'s',c:c2}],'T_env','value',{logX:1,yMin:0,yMax:2.2});
  lc('cD',EN,'t',[{k:'e',c:c0}],'tau_reset','E_tax ratio',{logX:1,yMin:0,yMax:3.5});
}

addEventListener('DOMContentLoaded',()=>{resetSim();drawCharts();document.getElementById('kVal').textContent=getK().toFixed(2);document.getElementById('gVal').textContent=getG().toFixed(2)});
addEventListener('resize',()=>{drawSim();drawCharts()});
