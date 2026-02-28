
// ====== GRAPH DATA ======
const N = 24;
const NODES = [
  {name:'ALML',type:'source'},{name:'ALMR',type:'source'},{name:'AVM',type:'source'},
  {name:'PLML',type:'source'},{name:'PLMR',type:'source'},{name:'PVM',type:'source'},
  {name:'AVD',type:'inter'},{name:'PVC',type:'inter'},{name:'AVA',type:'inter'},{name:'AVB',type:'inter'},
  {name:'VA1',type:'target'},{name:'VA2',type:'target'},{name:'VA3',type:'target'},{name:'VA4',type:'target'},
  {name:'DA1',type:'target'},{name:'DA2',type:'target'},{name:'DA3',type:'target'},
  {name:'VB1',type:'target'},{name:'VB2',type:'target'},{name:'VB3',type:'target'},{name:'VB4',type:'target'},
  {name:'DB1',type:'target'},{name:'DB2',type:'target'},{name:'DB3',type:'target'}
];
const EDGES = [[0,6,3],[0,1,2],[0,7,1],[1,6,3],[1,7,1],[2,6,3],[3,7,3],[3,4,2],[3,6,1],[4,7,3],[4,6,1],[5,7,2],[6,8,2],[6,10,1],[6,11,1],[7,9,2],[7,21,1],[7,22,1],[8,10,3],[8,14,3],[8,11,1],[8,12,1],[8,15,1],[9,17,3],[9,21,3],[9,18,1],[9,19,1],[9,22,1],[10,11,1],[11,12,1],[12,13,1],[13,14,1],[14,15,1],[15,16,1],[16,17,1],[17,18,1],[18,19,1],[19,20,1],[20,21,1],[21,22,1],[22,23,1]];
// Full adjacency matrix W[N][N]
const W=[[0,2,0,0,0,0,3,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[2,0,0,0,0,0,3,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,2,0,1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,2,0,0,1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],[3,3,3,1,1,0,0,0,2,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0],[1,1,0,3,3,2,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,1,1,0],[0,0,0,0,0,0,2,0,0,0,3,1,1,0,3,1,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,3,1,1,0,3,1,0],[0,0,0,0,0,0,1,0,3,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,1,0,1,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,1,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,3,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,1,0,1,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,1,0,0,0,0],[0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,0,1,0,0,0],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0],[0,0,0,0,0,0,0,1,0,3,0,0,0,0,0,0,0,0,0,0,1,0,1,0],[0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,1],[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0]];
const SRC_IDX = [0,1,2,3,4,5]; // sensory
const TGT_IDX = [10,11,12,13,14,15,16,17,18,19,20,21,22,23]; // motor

// ====== COMPLEX MATH HELPERS ======
// rho stored as Float64Array of length 2*N*N (re,im pairs: [re00,im00,re01,im01,...])
function cIdx(i,j){ return 2*(i*N+j); }
function rhoRe(rho,i,j){ return rho[cIdx(i,j)]; }
function rhoIm(rho,i,j){ return rho[cIdx(i,j)+1]; }

function newRho(){
  const r = new Float64Array(2*N*N);
  // rho_0 = uniform over sources
  const p = 1.0/SRC_IDX.length;
  SRC_IDX.forEach(s => { r[cIdx(s,s)] = p; });
  return r;
}

// Build Hamiltonian H = -(D - A) + epsilon*diag(random)
let H_re, H_im, disorderVec;
function buildH(epsilon){
  H_re = new Float64Array(N*N);
  H_im = new Float64Array(N*N); // H is real symmetric
  // H_ij = W_ij (off-diagonal hopping)
  // H_ii = -sum_j W_ij + epsilon_i (on-site)
  for(let i=0;i<N;i++){
    let deg = 0;
    for(let j=0;j<N;j++){
      if(i!==j && W[i][j]>0){
        H_re[i*N+j] = W[i][j]; // hopping
        deg += W[i][j];
      }
    }
    H_re[i*N+i] = -deg + epsilon * disorderVec[i];
  }
}

// drho/dt = -i[H,rho] + kappa*Sum_k(Z_k rho Z_k - rho) + gamma*sink
// For pure dephasing: off-diag decay at rate kappa
// For sink: diagonal decay at rate gamma for target nodes
function lindblad_rhs(rho, kappa, gamma, out){
  // Commutator: [H,rho] = Hrho - rhoH
  // (Hrho)_ij = Sum_k H_ik rho_kj
  // We need: drho/dt_ij = -i(Hrho - rhoH)_ij + dephasing + sink

  for(let i=0;i<N;i++){
    for(let j=0;j<N;j++){
      const idx = cIdx(i,j);
      // Compute (Hrho)_ij and (rhoH)_ij
      let hp_re=0, hp_im=0, ph_re=0, ph_im=0;
      for(let k=0;k<N;k++){
        // H is real: H_ik * rho_kj
        const h_ik = H_re[i*N+k];
        if(h_ik !== 0){
          hp_re += h_ik * rho[cIdx(k,j)];
          hp_im += h_ik * rho[cIdx(k,j)+1];
        }
        // rho_ik * H_kj (H real)
        const h_kj = H_re[k*N+j];
        if(h_kj !== 0){
          ph_re += rho[cIdx(i,k)] * h_kj;
          ph_im += rho[cIdx(i,k)+1] * h_kj;
        }
      }
      // -i * (Hrho - rhoH): multiply (a+bi) by -i = b - ai
      const comm_re = hp_re - ph_re;
      const comm_im = hp_im - ph_im;
      let drho_re = comm_im;  // -i*(re+i*im) = im - i*re
      let drho_im = -comm_re;

      // Dephasing: for i!=j, add -kappa * rho_ij
      if(i !== j){
        drho_re -= kappa * rho[idx];
        drho_im -= kappa * rho[idx+1];
      }

      // Sink on target nodes: -gamma/2 * (is_target(i) + is_target(j)) * rho_ij
      const ti = TGT_IDX.includes(i) ? 1 : 0;
      const tj = TGT_IDX.includes(j) ? 1 : 0;
      if(ti + tj > 0){
        const rate = gamma * 0.5 * (ti + tj);
        drho_re -= rate * rho[idx];
        drho_im -= rate * rho[idx+1];
      }

      out[idx] = drho_re;
      out[idx+1] = drho_im;
    }
  }
}

// Pre-compute target lookup for speed
const isTgt = new Uint8Array(N);
TGT_IDX.forEach(t => isTgt[t]=1);

// Optimized lindblad_rhs with isTgt lookup
function lindblad_fast(rho, kappa, gamma, out){
  for(let i=0;i<N;i++){
    for(let j=0;j<N;j++){
      const idx = cIdx(i,j);
      let hp_re=0,hp_im=0,ph_re=0,ph_im=0;
      for(let k=0;k<N;k++){
        const h_ik = H_re[i*N+k];
        if(h_ik){
          const ci = cIdx(k,j);
          hp_re += h_ik * rho[ci];
          hp_im += h_ik * rho[ci+1];
        }
        const h_kj = H_re[k*N+j];
        if(h_kj){
          const ci2 = cIdx(i,k);
          ph_re += rho[ci2] * h_kj;
          ph_im += rho[ci2+1] * h_kj;
        }
      }
      let dr = (hp_im - ph_im);
      let di = -(hp_re - ph_re);
      if(i!==j){ dr -= kappa*rho[idx]; di -= kappa*rho[idx+1]; }
      const s = gamma*0.5*(isTgt[i]+isTgt[j]);
      if(s){ dr -= s*rho[idx]; di -= s*rho[idx+1]; }
      out[idx] = dr;
      out[idx+1] = di;
    }
  }
}

// RK4 step
const k1=new Float64Array(2*N*N), k2=new Float64Array(2*N*N), k3=new Float64Array(2*N*N), k4=new Float64Array(2*N*N), tmp=new Float64Array(2*N*N);

function rk4_step(rho, dt, kappa, gamma){
  const L = 2*N*N;
  lindblad_fast(rho, kappa, gamma, k1);
  for(let i=0;i<L;i++) tmp[i] = rho[i] + 0.5*dt*k1[i];
  lindblad_fast(tmp, kappa, gamma, k2);
  for(let i=0;i<L;i++) tmp[i] = rho[i] + 0.5*dt*k2[i];
  lindblad_fast(tmp, kappa, gamma, k3);
  for(let i=0;i<L;i++) tmp[i] = rho[i] + dt*k3[i];
  lindblad_fast(tmp, kappa, gamma, k4);
  for(let i=0;i<L;i++) rho[i] += (dt/6)*(k1[i] + 2*k2[i] + 2*k3[i] + k4[i]);
}

// ====== SIMULATION STATE ======
let rho, simTime=0, playing=false, animId=null;
const dt = 0.01;
const stepsPerFrame = 5;

// Fixed disorder seed
disorderVec = new Float64Array(N);
(function(){
  // Seeded pseudo-random
  let s = 42;
  function r(){s=(s*1664525+1013904223)&0xFFFFFFFF;return(s>>>0)/4294967296;}
  for(let i=0;i<N;i++) disorderVec[i] = 2*r()-1;
})();

function getKappa(){ return Math.pow(10, parseFloat(document.getElementById('kappaSlider').value)); }
function getEps(){ return parseFloat(document.getElementById('epsSlider').value); }
function getGamma(){ return parseFloat(document.getElementById('gammaSlider').value); }

function resetSim(){
  const eps = getEps();
  buildH(eps);
  rho = newRho();
  simTime = 0;
  drawSim();
  updateInfo();
}

function togglePlay(){
  playing = !playing;
  document.getElementById('playBtn').textContent = playing ? 'Pause' : 'Play';
  if(playing) animate();
  else if(animId){ cancelAnimationFrame(animId); animId=null; }
}

function animate(){
  if(!playing) return;
  const kappa = getKappa(), gamma = getGamma();
  for(let s=0;s<stepsPerFrame;s++){
    rk4_step(rho, dt, kappa, gamma);
    simTime += dt;
  }
  drawSim();
  updateInfo();
  animId = requestAnimationFrame(animate);
}

function updateInfo(){
  let pT=0, pS=0, tr=0;
  for(let i=0;i<N;i++){
    const p = rho[cIdx(i,i)];
    tr += p;
    if(isTgt[i]) pT += p;
    if(SRC_IDX.includes(i)) pS += p;
  }
  document.getElementById('infoBar').textContent =
    `t=${simTime.toFixed(2)} | P_target=${pT.toFixed(4)} | P_source=${pS.toFixed(4)} | Tr(rho)=${tr.toFixed(4)}`;
}

// ====== GRAPH VISUALIZATION ======
// Layout: 4 columns (Sensory, Command, Backward motor, Forward motor)
const nodePos = [];
function computeLayout(W_canvas, H_canvas){
  const pad = 50;
  // Group by type/function
  const groups = [
    SRC_IDX,           // col 0: sensory
    [6,7,8,9],         // col 1: interneurons
    [10,11,12,13,14,15,16], // col 2: backward motor (VA,DA)
    [17,18,19,20,21,22,23]  // col 3: forward motor (VB,DB)
  ];
  const colX = [pad+30, pad+160, pad+320, pad+480].map(x => x*(W_canvas-2*pad)/520 + pad);

  groups.forEach((g, ci) => {
    const gap = (H_canvas - 2*pad) / (g.length + 1);
    g.forEach((ni, gi) => {
      nodePos[ni] = { x: colX[ci], y: pad + gap*(gi+1) };
    });
  });
}

function css(v){ return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }

function drawSim(){
  const c = document.getElementById('simCanvas');
  const ctx = c.getContext('2d');
  const dpr = window.devicePixelRatio||1;
  const CW = c.clientWidth, CH = c.clientHeight;
  c.width = CW*dpr; c.height = CH*dpr;
  ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,CW,CH);

  if(nodePos.length === 0) computeLayout(CW, CH);
  // Recompute on resize
  if(Math.abs(nodePos[0].x - 0) < 1) computeLayout(CW, CH);

  const cSrc = css('--c-src'), cTgt = css('--c-tgt'), cInt = css('--c-int');
  const borderCol = css('--border');
  const textCol = css('--text-3');

  // Draw edges
  ctx.lineWidth = 1;
  EDGES.forEach(([a,b,w]) => {
    const pa = nodePos[a], pb = nodePos[b];
    if(!pa||!pb) return;
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y);
    ctx.strokeStyle = borderCol + '66';
    ctx.lineWidth = Math.max(0.5, w*0.5);
    ctx.stroke();
  });

  // Draw nodes sized by rho_ii
  const maxR = 18, minR = 4;
  const colors = {source: cSrc, inter: cInt, target: cTgt};

  for(let i=0;i<N;i++){
    const p = nodePos[i]; if(!p) continue;
    const pop = Math.max(0, rho[cIdx(i,i)]);
    const r = minR + pop * (maxR - minR) / 0.2; // scale: 0.2 = big
    const clampR = Math.min(Math.max(r, minR), maxR);

    ctx.beginPath();
    ctx.arc(p.x, p.y, clampR, 0, Math.PI*2);
    const col = colors[NODES[i].type];
    ctx.fillStyle = col;
    ctx.globalAlpha = 0.3 + pop*4; // brighter = more population
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = col;
    ctx.stroke();

    // Label
    ctx.fillStyle = textCol;
    ctx.font = '9px ' + css('--font-mono');
    ctx.textAlign = 'center';
    ctx.fillText(NODES[i].name, p.x, p.y + clampR + 12);

    // Population text
    if(pop > 0.005){
      ctx.fillStyle = css('--text');
      ctx.font = '600 8px ' + css('--font-mono');
      ctx.fillText(pop.toFixed(3), p.x, p.y + 3);
    }
  }

  // Column labels
  ctx.font = '600 11px ' + css('--font-body');
  ctx.fillStyle = textCol;
  ctx.textAlign = 'center';
  const labels = ['Sensory','Command','Motor (back)','Motor (fwd)'];
  const groups = [SRC_IDX, [6,7,8,9], [10,11,12,13,14,15,16], [17,18,19,20,21,22,23]];
  groups.forEach((g,i) => {
    const x = nodePos[g[0]].x;
    ctx.fillText(labels[i], x, 18);
  });
}

// ====== SLIDERS ======
document.getElementById('kappaSlider').addEventListener('input', function(){
  document.getElementById('kappaVal').textContent = getKappa().toFixed(2);
});
document.getElementById('epsSlider').addEventListener('input', function(){
  document.getElementById('epsVal').textContent = getEps().toFixed(2);
  resetSim(); // rebuild H with new epsilon
});
document.getElementById('gammaSlider').addEventListener('input', function(){
  document.getElementById('gammaVal').textContent = getGamma().toFixed(2);
});

// ====== STATIC CHARTS ======
const KDATA=[{k:.001,p:.4085},{k:.01,p:.5255},{k:.05,p:.7969},{k:.1,p:.912},{k:.3,p:.9861},{k:.5,p:.9934},{k:1,p:.9964},{k:3,p:.9972},{k:5,p:.9965},{k:10,p:.9927},{k:30,p:.9487},{k:50,p:.8762}];
const EDATA=[{e:0,c:.9978,t:.9999,q:.5986},{e:.3,c:.9977,t:.9999,q:.5993},{e:.5,c:.9975,t:1,q:.5551},{e:1,c:.9972,t:.9999,q:.3934},{e:1.5,c:.9967,t:.9996,q:.4627},{e:2,c:.996,t:.9952,q:.4594},{e:3,c:.9943,t:.9269,q:.4323}];
const TDATA=[{x:.1,c:.9972,t:.7164,q:.3934},{x:.3,c:.9972,t:.8946,q:.3934},{x:.5,c:.9972,t:.9952,q:.3934},{x:1,c:.9972,t:.9999,q:.3934},{x:2,c:.9972,t:1,q:.3934},{x:5,c:.9972,t:.9999,q:.3934},{x:10,c:.9972,t:.9999,q:.3934}];
const NDATA=[{n:1,c:.8609,t:.8981,q:.2389},{n:2,c:.9922,t:.9732,q:.3697},{n:3,c:.9972,t:.9999,q:.3934},{n:6,c:.9999,t:1,q:.5071},{n:14,c:1,t:1,q:.512}];

function lineChart(id,data,xk,yks,xLab,yLab,opts={}){
  const c=document.getElementById(id);const ctx=c.getContext('2d');const dpr=window.devicePixelRatio||1;
  const CW=c.clientWidth,CH=c.clientHeight;c.width=CW*dpr;c.height=CH*dpr;ctx.scale(dpr,dpr);ctx.clearRect(0,0,CW,CH);
  const ml=52,mr=12,mt=12,mb=32,pw=CW-ml-mr,ph=CH-mt-mb;
  const allY=[];data.forEach(d=>yks.forEach(y=>{if(d[y.k]!=null)allY.push(d[y.k])}));
  if(opts.hl)opts.hl.forEach(h=>allY.push(h.v));
  const yMin=opts.yMin??Math.min(...allY)*.95,yMax=opts.yMax??Math.max(...allY)*1.02;
  const xVals=data.map(d=>d[xk]),useLog=opts.logX;
  const xLog=useLog?xVals.map(v=>Math.log10(v)):xVals;
  const xMin=Math.min(...xLog),xMax=Math.max(...xLog);
  const toX=v=>ml+((useLog?Math.log10(v):v)-xMin)/(xMax-xMin)*pw;
  const toY=v=>mt+(1-(v-yMin)/(yMax-yMin))*ph;
  // Grid
  ctx.strokeStyle=css('--border-light');ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const y=mt+ph*i/4;ctx.beginPath();ctx.moveTo(ml,y);ctx.lineTo(ml+pw,y);ctx.stroke();}
  // Hlines
  if(opts.hl)opts.hl.forEach(h=>{ctx.setLineDash([4,4]);ctx.strokeStyle=h.c;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(ml,toY(h.v));ctx.lineTo(ml+pw,toY(h.v));ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=h.c;ctx.font='9px '+css('--font-mono');ctx.textAlign='right';ctx.fillText(h.l,ml+pw,toY(h.v)-3);});
  // Lines
  yks.forEach(yk=>{ctx.strokeStyle=yk.c;ctx.lineWidth=2;ctx.beginPath();let f=1;data.forEach(d=>{if(d[yk.k]==null)return;const x=toX(d[xk]),y=toY(d[yk.k]);f?(ctx.moveTo(x,y),f=0):ctx.lineTo(x,y)});ctx.stroke();data.forEach(d=>{if(d[yk.k]==null)return;ctx.beginPath();ctx.arc(toX(d[xk]),toY(d[yk.k]),3,0,Math.PI*2);ctx.fillStyle=yk.c;ctx.fill()})});
  // Peak
  if(opts.peak){let b=data[0],bv=-Infinity;const pk=yks[0].k;data.forEach(d=>{if(d[pk]>bv){bv=d[pk];b=d}});const px=toX(b[xk]),py=toY(bv);ctx.beginPath();ctx.arc(px,py,6,0,Math.PI*2);ctx.strokeStyle=yks[0].c;ctx.lineWidth=2;ctx.stroke();ctx.fillStyle=css('--text');ctx.font='600 10px '+css('--font-mono');ctx.textAlign='center';ctx.fillText('k*='+b[xk],px,py-10)}
  // Axes
  ctx.fillStyle=css('--text-3');ctx.font='500 10px '+css('--font-body');ctx.textAlign='center';ctx.fillText(xLab,ml+pw/2,CH-4);
  ctx.save();ctx.translate(10,mt+ph/2);ctx.rotate(-Math.PI/2);ctx.fillText(yLab,0,0);ctx.restore();
  ctx.font='9px '+css('--font-mono');ctx.textAlign='right';
  for(let i=0;i<=4;i++){const v=yMin+(yMax-yMin)*i/4;ctx.fillText(v.toFixed(2),ml-4,mt+ph*(1-i/4)+3)}
}

function drawStaticCharts(){
  const cc=css('--c-crn'),ct=css('--c-th'),cq=css('--c-ctqw');
  lineChart('chartK',KDATA,'k',[{k:'p',c:cc}],'kappa','P_crn',{logX:1,yMin:.3,yMax:1.05,peak:1,hl:[{v:.9999,c:ct,l:'Thermal'},{v:.3934,c:cq,l:'CTQW'}]});
  lineChart('chartE',EDATA,'e',[{k:'c',c:cc},{k:'t',c:ct},{k:'q',c:cq}],'epsilon','P',{yMin:.3,yMax:1.05});
  lineChart('chartT',TDATA,'x',[{k:'c',c:cc},{k:'t',c:ct},{k:'q',c:cq}],'T_env','P',{logX:1,yMin:.3,yMax:1.05});
  lineChart('chartN',NDATA,'n',[{k:'c',c:cc},{k:'t',c:ct},{k:'q',c:cq}],'n_targets','P',{yMin:.2,yMax:1.05});
}

// ====== INIT ======
window.addEventListener('DOMContentLoaded', () => {
  resetSim();
  drawStaticCharts();
  document.getElementById('kappaVal').textContent = getKappa().toFixed(2);
  document.getElementById('epsVal').textContent = getEps().toFixed(2);
  document.getElementById('gammaVal').textContent = getGamma().toFixed(2);
});
window.addEventListener('resize', () => {
  nodePos.length = 0;
  drawSim();
  drawStaticCharts();
});
