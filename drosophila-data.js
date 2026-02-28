
const generateConnectome=()=>{const nodes=[],edges=[];const numPN=100,numKC=1000,numMBON=24,numOther=1832;let id=0;
for(let i=0;i<numPN;i++)nodes.push({id:id++,type:'PN',layer:0,x:0,y:0});
for(let i=0;i<numKC;i++)nodes.push({id:id++,type:'KC',layer:1,x:0,y:0});
for(let i=0;i<numMBON;i++)nodes.push({id:id++,type:'MBON',layer:2,x:0,y:0});
for(let i=0;i<numOther;i++)nodes.push({id:id++,type:'other',layer:Math.random()<.5?0:1,x:0,y:0});
for(let k=numPN;k<numPN+numKC;k++){const n=5+Math.floor(Math.random()*4);for(let i=0;i<n;i++)edges.push({source:Math.floor(Math.random()*numPN),target:k,weight:1+Math.random()*5})}
const ms=numPN+numKC;for(let i=0;i<numMBON;i++){const n=50+Math.floor(Math.random()*100);for(let j=0;j<n;j++)edges.push({source:numPN+Math.floor(Math.random()*numKC),target:ms+i,weight:1+Math.random()*3})}
for(let i=0;i<15000;i++){const s=Math.floor(Math.random()*nodes.length),t=Math.floor(Math.random()*nodes.length);if(s!==t)edges.push({source:s,target:t,weight:Math.random()*2})}
return {nodes,edges}};
const {nodes,edges}=generateConnectome();
const canvas=document.getElementById('connectomeCanvas');
const ctx=canvas.getContext('2d');
const W=canvas.width,H=canvas.height;
function getCS(name){return getComputedStyle(document.documentElement).getPropertyValue(name).trim()}
const layouts={};
layouts.force=()=>{nodes.forEach(n=>{n.x=W*.2+Math.random()*W*.6;n.y=H*.2+Math.random()*H*.6;n.vx=0;n.vy=0});
for(let it=0;it<100;it++){for(let i=0;i<Math.min(nodes.length,500);i++)for(let j=i+1;j<Math.min(nodes.length,500);j++){const dx=nodes[j].x-nodes[i].x,dy=nodes[j].y-nodes[i].y,d=Math.sqrt(dx*dx+dy*dy)+1,f=500/(d*d);nodes[i].vx-=f*dx/d;nodes[i].vy-=f*dy/d;nodes[j].vx+=f*dx/d;nodes[j].vy+=f*dy/d}
for(let i=0;i<Math.min(edges.length,1000);i++){const e=edges[Math.floor(Math.random()*edges.length)],s=nodes[e.source],t=nodes[e.target],dx=t.x-s.x,dy=t.y-s.y,d=Math.sqrt(dx*dx+dy*dy)+1,f=d*.001;s.vx+=f*dx/d;s.vy+=f*dy/d;t.vx-=f*dx/d;t.vy-=f*dy/d}
nodes.forEach(n=>{n.x+=n.vx*.1;n.y+=n.vy*.1;n.vx*=.8;n.vy*=.8;n.x=Math.max(50,Math.min(W-50,n.x));n.y=Math.max(50,Math.min(H-50,n.y))})}};
layouts.circular=()=>{const cx=W/2,cy=H/2,r=Math.min(W,H)*.4;nodes.forEach((n,i)=>{const a=i/nodes.length*2*Math.PI;n.x=cx+r*Math.cos(a);n.y=cy+r*Math.sin(a)})};
layouts.hierarchical=()=>{const lh=H/4;nodes.forEach(n=>{let y;const pnList=nodes.filter(m=>m.type==='PN'),kcList=nodes.filter(m=>m.type==='KC'),mbonList=nodes.filter(m=>m.type==='MBON');
if(n.type==='PN'){y=lh*.5;n.x=(W-W*.3)/2+pnList.indexOf(n)/100*W*.3}
else if(n.type==='KC'){y=lh*1.5;n.x=(W-W*.8)/2+kcList.indexOf(n)/1000*W*.8}
else if(n.type==='MBON'){y=lh*2.5;n.x=(W-W*.4)/2+mbonList.indexOf(n)/24*W*.4}
else{y=lh*.5+n.layer;n.x=100+Math.random()*(W-200)}
n.y=y+(Math.random()-.5)*30})};
layouts.hierarchical();
let nodeS=3,edgeO=0.15;
function render(){
  const bg=getCS('--canvas-bg')||'#f7f8fb';
  ctx.fillStyle=bg;ctx.fillRect(0,0,W,H);
  const accentC=getCS('--accent')||'#3b4cc0',tealC=getCS('--teal')||'#0d8a7c',warmC=getCS('--warm')||'#c47d0a';
  const colors={PN:accentC,KC:tealC,MBON:warmC,other:'#b8bcc8'};
  ctx.globalAlpha=edgeO;ctx.strokeStyle=getCS('--text-3')||'#8b8f9e';ctx.lineWidth=0.5;
  const es=Math.min(edges.length,5000);for(let i=0;i<es;i++){const e=edges[Math.floor(Math.random()*edges.length)],s=nodes[e.source],t=nodes[e.target];ctx.beginPath();ctx.moveTo(s.x,s.y);ctx.lineTo(t.x,t.y);ctx.stroke()}
  ctx.globalAlpha=1;nodes.forEach(n=>{ctx.fillStyle=colors[n.type];ctx.beginPath();ctx.arc(n.x,n.y,nodeS,0,2*Math.PI);ctx.fill()});
}
document.getElementById('layoutType').addEventListener('change',e=>{layouts[e.target.value]();render()});
document.getElementById('nodeSize').addEventListener('input',e=>{nodeS=parseFloat(e.target.value);render()});
document.getElementById('edgeOpacity').addEventListener('input',e=>{edgeO=parseFloat(e.target.value);render()});
render();
document.getElementById('nodeCount').textContent=nodes.length.toLocaleString();
document.getElementById('edgeCount').textContent=edges.length.toLocaleString();
