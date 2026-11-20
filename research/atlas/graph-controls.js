// Sidebar tooltips reuse vis-network's .vis-tooltip style and 100ms tooltipDelay.
// Names get one only when CSS ellipsis truncates them (the full text is still in
// the DOM); counts always get one, to say what the number is. Text is set with
// textContent only (labels are untrusted). Delegated on document so rows rebuilt
// later (search results, showInfo()) are covered.
const sidebarTip = document.createElement('div');
sidebarTip.className = 'vis-tooltip';
sidebarTip.style.cssText = 'white-space: normal; max-width: 360px; overflow-wrap: break-word;';
document.body.appendChild(sidebarTip);
let sidebarTipTimer = null;
let sidebarTipEl = null;    // element whose text the tooltip shows
let sidebarTipZone = null;  // element the pointer must leave to hide it
function hideSidebarTip() {
  clearTimeout(sidebarTipTimer);
  sidebarTip.style.visibility = 'hidden';
  sidebarTip.textContent = '';
  sidebarTipEl = sidebarTipZone = null;
}
document.addEventListener('mouseover', e => {
  const zone = e.target.closest && e.target.closest('.legend-count, .legend-item, .search-item, .neighbor-link');
  // Anywhere on a legend row except its count (dot, checkbox, gaps, padding)
  // stands for the row's name, so moving within the row never re-triggers it.
  const el = zone && zone.classList.contains('legend-item') ? zone.querySelector('.legend-label') : zone;
  if (!el || el === sidebarTipEl) return;
  hideSidebarTip();
  const isCount = el.classList.contains('legend-count');
  if (!isCount && el.scrollWidth <= el.clientWidth) return;
  const text = isCount ? `${el.textContent} ${el.textContent === '1' ? 'node' : 'nodes'}` : el.textContent;
  sidebarTipEl = el;
  sidebarTipZone = zone;
  const x = e.clientX, y = e.clientY;
  sidebarTipTimer = setTimeout(() => {
    sidebarTip.textContent = text;
    sidebarTip.style.left = sidebarTip.style.top = '0px';  // measure at full max-width
    sidebarTip.style.visibility = 'visible';
    const w = sidebarTip.offsetWidth, h = sidebarTip.offsetHeight;
    sidebarTip.style.left = Math.max(4, Math.min(x + 12, window.innerWidth - w - 4)) + 'px';
    sidebarTip.style.top = (y + 16 + h > window.innerHeight ? Math.max(4, y - h - 8) : y + 16) + 'px';
  }, 100);
});
document.addEventListener('mouseout', e => {
  if (sidebarTipZone && !sidebarTipZone.contains(e.relatedTarget)) hideSidebarTip();
});
// A click rebuilds or hides the row (showInfo(), search pick) without a mouseout.
document.addEventListener('mousedown', hideSidebarTip);

// Track hovered node — hover detection is more reliable than click params
network.on('selectNode', p => { if (p.nodes.length) showInfo(p.nodes[0]); });
let hoveredNodeId = null;
network.on('hoverNode', params => {
  hoveredNodeId = params.node;
  container.style.cursor = 'pointer';
});
network.on('blurNode', () => {
  hoveredNodeId = null;
  container.style.cursor = 'default';
});
container.addEventListener('click', () => {
  if (hoveredNodeId !== null) {
    showInfo(hoveredNodeId);
    network.selectNodes([hoveredNodeId]);
  }
});
network.on('click', params => {
  if (params.nodes.length > 0) {
    showInfo(params.nodes[0]);
  } else if (hoveredNodeId === null) {
    document.getElementById('info-content').innerHTML = '<span class="empty">Click a node to inspect it</span>';
  }
});

const searchInput = document.getElementById('search');
const searchResults = document.getElementById('search-results');
searchInput.addEventListener('input', () => {
  const q = searchInput.value.toLowerCase().trim();
  searchResults.innerHTML = '';
  if (!q) { searchResults.style.display = 'none'; return; }
  const matches = RAW_NODES.filter(n => n.label.toLowerCase().includes(q)).slice(0, 20);
  if (!matches.length) { searchResults.style.display = 'none'; return; }
  searchResults.style.display = 'block';
  matches.forEach(n => {
    const el = document.createElement('div');
    el.className = 'search-item';
    el.textContent = n.label;
    el.style.borderLeft = `3px solid ${n.color.background}`;
    el.style.paddingLeft = '8px';
    el.onclick = () => {
      network.focus(n.id, { scale: 1.5, animation: true });
      network.selectNodes([n.id]);
      showInfo(n.id);
      searchResults.style.display = 'none';
      searchInput.value = '';
    };
    searchResults.appendChild(el);
  });
});
document.addEventListener('click', e => {
  if (!searchResults.contains(e.target) && e.target !== searchInput)
    searchResults.style.display = 'none';
});

const hiddenCommunities = new Set();

const selectAllCb = document.getElementById('select-all-cb');

function updateSelectAllState() {
  const total = LEGEND.length;
  const hidden = hiddenCommunities.size;
  selectAllCb.checked = hidden === 0;
  selectAllCb.indeterminate = hidden > 0 && hidden < total;
}

function toggleAllCommunities(hide) {
  document.querySelectorAll('.legend-item').forEach(item => {
    hide ? item.classList.add('dimmed') : item.classList.remove('dimmed');
  });
  document.querySelectorAll('.legend-cb').forEach(cb => {
    cb.checked = !hide;
  });
  LEGEND.forEach(c => {
    if (hide) hiddenCommunities.add(c.cid); else hiddenCommunities.delete(c.cid);
  });
  const updates = RAW_NODES.map(n => ({ id: n.id, hidden: hide }));
  nodesDS.update(updates);
  updateSelectAllState();
}

const legendEl = document.getElementById('legend');
LEGEND.forEach(c => {
  const item = document.createElement('div');
  item.className = 'legend-item';
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.className = 'legend-cb';
  cb.checked = true;
  cb.addEventListener('change', (e) => {
    e.stopPropagation();
    if (cb.checked) {
      hiddenCommunities.delete(c.cid);
      item.classList.remove('dimmed');
    } else {
      hiddenCommunities.add(c.cid);
      item.classList.add('dimmed');
    }
    const updates = RAW_NODES
      .filter(n => n.community === c.cid)
      .map(n => ({ id: n.id, hidden: !cb.checked }));
    nodesDS.update(updates);
    updateSelectAllState();
  });
  item.innerHTML = `<div class="legend-dot" style="background:${c.color}"></div>
    <span class="legend-label">${c.label}</span>
    <span class="legend-count">${c.count}</span>`;
  item.prepend(cb);
  item.onclick = (e) => {
    if (e.target === cb) return;
    cb.checked = !cb.checked;
    cb.dispatchEvent(new Event('change'));
  };
  legendEl.appendChild(item);
});
selectAllCb.onchange=()=>toggleAllCommunities(!selectAllCb.checked);
document.querySelector('#fit').onclick=()=>network.fit({animation:true});
for(const [id,factor] of [['zoom-in',1.45],['zoom-out',1/1.45]]){
  document.getElementById(id).onclick=()=>network.moveTo({scale:network.getScale()*factor,animation:true});
}
const requestedNode = new URLSearchParams(location.search).get('node');
if (requestedNode && nodesDS.get(requestedNode)) {
  network.once('stabilizationIterationsDone', () => focusNode(requestedNode));
  showInfo(requestedNode);
}
