(()=>{
  const A=Atlas,{data,state,$,esc}=A;
  $('region-list').innerHTML=data.regions.map(r=>`<button data-region="${esc(r.id)}"><span class="dot" style="background:${esc(r.color)}"></span>${esc(r.label)}<small>${data.nodes.filter(n=>n.region===r.id).length}</small></button>`).join('');
  document.querySelectorAll('[data-region]').forEach(b=>b.onclick=()=>{state.region=b.dataset.region;state.route=null;state.query='';state.selected=null;$('search').value='';A.draw();A.regionPanel(state.region);});
  $('routes').innerHTML=data.routes.map(r=>`<button data-route="${esc(r.id)}">↗ ${esc(r.label)}</button>`).join('');
  document.querySelectorAll('[data-route]').forEach(b=>b.onclick=()=>{state.route=b.dataset.route;state.region=null;state.query='';state.selected=null;state.lens='all';$('lens').value='all';$('search').value='';A.draw();const r=data.routes.find(x=>x.id===state.route);$('detail-content').innerHTML=`<span class="badge">Связанный маршрут</span><h2 class="detail-title">${esc(r.label)}</h2><p class="claim">${esc(r.description)}</p><div class="result-list">${r.nodes.map(id=>`<button data-route-node="${esc(id)}">${esc(A.byId.get(id).label)}</button>`).join('')}</div>`;document.querySelectorAll('[data-route-node]').forEach(x=>x.onclick=()=>A.select(x.dataset.routeNode));});
  $('search').oninput=()=>{state.query=$('search').value;state.selected=null;state.region=null;state.route=null;A.draw();state.query?A.searchPanel():A.intro();};
  $('lens').onchange=()=>{state.lens=$('lens').value;state.selected=null;A.draw();};
  $('labels').onchange=()=>{state.labels=$('labels').checked;A.transform();};
  $('home').onclick=()=>{history.replaceState(null,'',location.pathname);Object.assign(state,{region:null,route:null,query:'',selected:null,lens:'all'});$('search').value='';$('lens').value='all';A.draw();A.intro();};
  $('zoom-in').onclick=()=>A.zoom(data.ui.zoomStep);$('zoom-out').onclick=()=>A.zoom(1/data.ui.zoomStep);
  const graph=$('graph');let drag=null;
  graph.addEventListener('wheel',e=>{e.preventDefault();const b=graph.getBoundingClientRect();A.zoom(Math.exp(-e.deltaY*data.ui.wheelSensitivity),e.clientX-b.left,e.clientY-b.top);},{passive:false});
  graph.addEventListener('pointerdown',e=>{if(e.target.closest('[data-id]')||e.target.closest('[data-edge]'))return;drag={x:e.clientX,y:e.clientY,ox:state.x,oy:state.y};graph.setPointerCapture(e.pointerId);});
  graph.addEventListener('pointermove',e=>{if(!drag)return;state.x=drag.ox+e.clientX-drag.x;state.y=drag.oy+e.clientY-drag.y;A.transform();});
  graph.addEventListener('pointerup',()=>drag=null);graph.addEventListener('pointercancel',()=>drag=null);
  $('coverage').textContent=`${data.nodes.length} утверждений · ${data.edges.length} связей · ${data.meta.sourcesRead} прочитанных источников. ${data.meta.coverageNote}`;
  new ResizeObserver(()=>A.draw()).observe($('canvas'));A.draw();if(location.hash)A.select(decodeURIComponent(location.hash.slice(1)));window.addEventListener('hashchange',()=>{if(location.hash)A.select(decodeURIComponent(location.hash.slice(1)));});
})();
