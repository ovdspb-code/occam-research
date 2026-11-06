/* Offline, source-linked scientific atlas. No network or analytics. */
const Atlas = (() => {
  const data=window.SFP_ATLAS, byId=new Map(data.nodes.map(n=>[n.id,n]));
  const regions=new Map(data.regions.map(r=>[r.id,r]));
  const state={region:null,route:null,query:'',lens:'all',selected:null,labels:false,scale:1,x:0,y:0};
  const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const status={established:'Установлено в корпусе',conditional:'Условный результат',hypothesis:'Гипотеза',refuted:'Проверка не пройдена',open:'Открытый вопрос',known:'Известный механизм'};
  const relations={requires:'требует',derives:'даёт следствие',generalizes:'обобщает',contradicts:'опровергает',limits:'ограничивает',analogy:'аналогия',open_bridge:'недостающий переход'};
  const svg=(tag,attrs={})=>{const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));return e;};
  function searchMatches(){const q=state.query.toLocaleLowerCase().trim();return q?data.nodes.filter(n=>[n.label,n.claim,n.domain,n.family,...n.assumptions].join(' ').toLocaleLowerCase().includes(q)):[];}
  function visible(){
    let nodes=data.nodes;
    if(state.region)nodes=nodes.filter(n=>n.region===state.region);
    if(state.route){const route=data.routes.find(r=>r.id===state.route);nodes=nodes.filter(n=>route.nodes.includes(n.id));}
    if(state.query){const ids=new Set(searchMatches().map(n=>n.id));nodes=nodes.filter(n=>ids.has(n.id));}
    if(state.selected){const ids=new Set([state.selected]);data.edges.forEach(e=>{if(e.source===state.selected)ids.add(e.target);if(e.target===state.selected)ids.add(e.source);});nodes=nodes.filter(n=>ids.has(n.id));}
    const ids=new Set(nodes.map(n=>n.id));
    let edges=data.edges.filter(e=>ids.has(e.source)&&ids.has(e.target));
    if(state.lens==='evidence')edges=edges.filter(e=>e.status==='EXTRACTED');
    if(state.lens==='bridges')edges=edges.filter(e=>byId.get(e.source).region!==byId.get(e.target).region);
    if(state.lens==='gaps')edges=edges.filter(e=>['open_bridge','limits','contradicts'].includes(e.relation));
    if(['bridges','gaps'].includes(state.lens)){const used=new Set(edges.flatMap(e=>[e.source,e.target]));nodes=nodes.filter(n=>used.has(n.id));}
    return {nodes,edges};
  }
  function select(id,remember=true){if(!byId.has(id))return;const hash='#'+encodeURIComponent(id);if(remember&&location.hash!==hash)history.pushState(null,'',hash);state.selected=id;state.query='';$('search').value='';state.region=null;state.route=null;state.lens='all';$('lens').value='all';draw();panelNode(id);}
  function draw(fit=true){
    let {nodes,edges}=visible();
    if(state.selected){const rest=nodes.filter(n=>n.id!==state.selected),radius=data.ui.focusRadius;nodes=nodes.map(n=>n.id===state.selected?{...n,x:0,y:0}:{...n,x:radius*Math.cos(-Math.PI/2+2*Math.PI*rest.findIndex(x=>x.id===n.id)/rest.length),y:radius*Math.sin(-Math.PI/2+2*Math.PI*rest.findIndex(x=>x.id===n.id)/rest.length)});}
    const positions=new Map(nodes.map(n=>[n.id,n]));$('nodes').replaceChildren();$('links').replaceChildren();$('zones').replaceChildren();
    const selected=state.selected,near=new Set([selected]);data.edges.forEach(e=>{if(e.source===selected)near.add(e.target);if(e.target===selected)near.add(e.source);});
    const zones=new Map();nodes.forEach(n=>{if(!zones.has(n.region))zones.set(n.region,[]);zones.get(n.region).push(n);});
    if(!state.selected)zones.forEach((items,id)=>{const r=regions.get(id),cx=items.reduce((a,n)=>a+n.x,0)/items.length,cy=Math.min(...items.map(n=>n.y))-45;const t=svg('text',{x:cx,y:cy,'text-anchor':'middle'});t.textContent=r.label;$('zones').append(t);});
    edges.forEach((e,i)=>{
      const s=positions.get(e.source),t=positions.get(e.target),mx=(s.x+t.x)/2,my=(s.y+t.y)/2;
      const bend=(i%2?1:-1)*Math.min(35,Math.hypot(t.x-s.x,t.y-s.y)*.08);
      const p=svg('path',{d:`M${s.x},${s.y} Q${mx+bend},${my-bend} ${t.x},${t.y}`,'data-edge':e.id,'marker-end':'url(#arrow)',stroke:e.relation==='contradicts'?'var(--red)':regions.get(s.region).color,class:[e.status==='EXTRACTED'?'':'inferred',e.relation,selected?(e.source===selected||e.target===selected?'selected':'dim'):''].join(' ')});
      p.addEventListener('click',()=>panelEdge(e));const title=svg('title');title.textContent=`${s.label} → ${t.label}: ${relations[e.relation]||e.relation}`;p.append(title);$('links').append(p);
    });
    nodes.forEach(n=>{
      const g=svg('g',{transform:`translate(${n.x},${n.y})`,'data-id':n.id,role:'button',tabindex:'0','aria-label':n.label,class:(selected===n.id?'selected ':selected&&!near.has(n.id)?'dim ':'')});
      g.append(svg('circle',{r:6,fill:regions.get(n.region).color,'stroke-dasharray':n.status==='hypothesis'||n.status==='open'?'2 2':'none'}));
      const txt=svg('text',{x:10,y:4,'data-anchor':n.anchor?'1':'0'});txt.textContent=n.label.length>data.ui.labelLength?n.label.slice(0,data.ui.labelLength-1)+'…':n.label;g.append(txt);
      const title=svg('title');title.textContent=`${n.label}\n${status[n.status]}\n${n.claim}`;g.append(title);
      g.addEventListener('click',()=>{select(n.id);});g.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();select(n.id);}});$('nodes').append(g);
    });
    $('empty').hidden=nodes.length>0;
    $('view-title').textContent=state.selected?'Связи выбранного утверждения':state.query?'Результаты поиска':state.region?regions.get(state.region).label:state.route?data.routes.find(r=>r.id===state.route).label:'Весь ландшафт';
    $('view-count').textContent=`Утверждения: ${nodes.length} · связи: ${edges.length}`;
    document.querySelectorAll('[data-region]').forEach(b=>b.classList.toggle('active',b.dataset.region===state.region));
    if(fit&&nodes.length)fitNodes(nodes);else transform();
  }
  function fitNodes(nodes){const box=$('graph').getBoundingClientRect(),xs=nodes.map(n=>n.x),ys=nodes.map(n=>n.y),minX=Math.min(...xs),minY=Math.min(...ys),width=Math.max(...xs)-minX,height=Math.max(...ys)-minY;state.scale=Math.min((box.width-120)/(width||1),(box.height-180)/(height||1),data.ui.maxZoom);state.x=(box.width-width*state.scale)/2-minX*state.scale;state.y=(box.height-height*state.scale)/2-minY*state.scale;transform();}
  function transform(){
    $('world').setAttribute('transform',`translate(${state.x},${state.y}) scale(${state.scale})`);$('zoom-label').textContent=`${Math.round(state.scale*100)}%`;
    $('nodes').querySelectorAll('circle').forEach(c=>c.setAttribute('r',6/state.scale));
    const box=$('graph').getBoundingClientRect(),occupied=[],compact=box.width<600&&!state.selected&&!state.region&&!state.route&&!state.query;
    $('zones').querySelectorAll('text').forEach(t=>{t.style.display=compact?'none':'';t.style.fontSize=`${13/state.scale}px`;const r=t.getBoundingClientRect();occupied.push(r);});
    const labels=[...$('nodes').querySelectorAll('text')].sort((a,b)=>Number(b.parentNode.dataset.id===state.selected)-Number(a.parentNode.dataset.id===state.selected)||Number(b.dataset.anchor)-Number(a.dataset.anchor));
    labels.forEach(t=>{t.style.fontSize=`${13/state.scale}px`;t.setAttribute('x',10/state.scale);t.setAttribute('y',4/state.scale);t.setAttribute('text-anchor','start');const id=t.parentNode.dataset.id,n=byId.get(id);const eligible=state.labels||(!compact&&(state.region||state.route||state.selected||state.query||t.dataset.anchor==='1'));t.style.display=eligible?'':'none';if(!eligible)return;let r=t.getBoundingClientRect();if(r.right>box.right-10){t.setAttribute('x',-10/state.scale);t.setAttribute('text-anchor','end');r=t.getBoundingClientRect();}if(id===state.selected){t.setAttribute('x',0);t.setAttribute('y',-15/state.scale);t.setAttribute('text-anchor','middle');r=t.getBoundingClientRect();}const gap=data.ui.labelGap,overlap=occupied.some(q=>r.left<q.right+gap&&r.right>q.left-gap&&r.top<q.bottom+gap&&r.bottom>q.top-gap);if(!state.labels&&!state.selected&&overlap)t.style.display='none';else occupied.push(r);});
  }
  function zoom(factor,cx,cy){const b=$('graph').getBoundingClientRect();cx??=b.width/2;cy??=b.height/2;const next=Math.max(data.ui.minZoom,Math.min(data.ui.maxZoom,state.scale*factor)),ratio=next/state.scale;state.x=cx-(cx-state.x)*ratio;state.y=cy-(cy-state.y)*ratio;state.scale=next;transform();}
  let panelNode=()=>{},panelEdge=()=>{};
  return {data,byId,regions,state,$,esc,status,relations,visible,searchMatches,draw,select,zoom,transform,setPanels:(n,e)=>{panelNode=n;panelEdge=e;}};
})();
