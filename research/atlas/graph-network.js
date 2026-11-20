// HTML-escape helper — prevents XSS when injecting graph data into innerHTML
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// Build vis datasets
const nodesDS = new vis.DataSet(RAW_NODES.map((n, i) => ({
  id: n.id, label: n.label, color: n.color, size: n.size, shape:n.shape || 'dot', borderWidth:n.borderWidth ?? 1.5, role:n.role,
  font: n.font, title: n.title,
  // Fermat/golden-angle spiral seed positions (#3699): spreading nodes out
  // before physics runs keeps avoidOverlap from computing near-zero-distance
  // repulsion that blows the BarnesHut recursion into a stack overflow on large
  // graphs. `i` is the map index — physics still settles small graphs identically.
  x: 30 * Math.sqrt(i) * Math.cos(i * 2.4),
  y: 30 * Math.sqrt(i) * Math.sin(i * 2.4),
  community: n.community, community_name: n.community_name,
  source_file: n.source_file, file_type: n.file_type, paper: n.paper, status: n.status, degree: n.degree,
  member_count: n.member_count,
})));

const edgesDS = new vis.DataSet(RAW_EDGES.map((e, i) => ({
  id: i, from: e.from, to: e.to,
  label: '',
  title: e.title,
  dashes: e.dashes,
  width: e.width,
  color: e.color,
  arrows: { to: { enabled: true, scaleFactor: 0.5 } },
})));

const container = document.getElementById('graph');
const network = new vis.Network(container, { nodes: nodesDS, edges: edgesDS }, {
  physics: {
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
      gravitationalConstant: -60,
      centralGravity: 0.005,
      springLength: 120,
      springConstant: 0.08,
      damping: 0.4,
      avoidOverlap: 0.8,
    },
    stabilization: { iterations: 200, fit: true },
  },
  interaction: {
    hover: true,
    tooltipDelay: 100,
    hideEdgesOnDrag: true,
    navigationButtons: false,
    keyboard: false,
  },
  nodes: { shape: 'dot', borderWidth: 1.5 },
  edges: { smooth: { type: 'continuous', roundness: 0.2 }, selectionWidth: 3 },
});

// Theme toggle (#3894): Light / Dark / System, persisted in localStorage.
const THEME_KEY = 'graphify-theme';
const themeMQ = window.matchMedia ? window.matchMedia('(prefers-color-scheme: light)') : null;
let themeLabelColor = '#ffffff';  // matches the per-node font color set in Python
function themePref() {
  let p = null;
  try { p = localStorage.getItem(THEME_KEY); } catch (e) {}
  return (p === 'light' || p === 'dark' || p === 'system') ? p : null;
}
function applyTheme(pref) {
  const t = pref === 'light' ? 'light' : (pref === 'system' && themeMQ && themeMQ.matches) ? 'light' : 'dark';
  const root = document.documentElement;
  if (!root) return;
  root.setAttribute('data-theme', t);
  document.querySelectorAll('[data-theme-choice]').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.themeChoice === (pref || 'dark')));
  });
  const labelColor = getComputedStyle(root).getPropertyValue('--node-label').trim();
  if (labelColor && labelColor !== themeLabelColor) {
    themeLabelColor = labelColor;
    nodesDS.update(nodesDS.get().map(n => ({ id: n.id, font: Object.assign({}, n.font, { color: labelColor }) })));
  }
}
document.querySelectorAll('[data-theme-choice]').forEach(b => {
  b.addEventListener('click', () => {
    const pref = b.dataset.themeChoice;
    try { localStorage.setItem(THEME_KEY, pref); } catch (e) {}
    applyTheme(pref);
  });
});
if (themeMQ) {
  const onSchemeChange = () => { if (themePref() === 'system') applyTheme('system'); };
  if (themeMQ.addEventListener) themeMQ.addEventListener('change', onSchemeChange);
  else if (themeMQ.addListener) themeMQ.addListener(onSchemeChange);
}
applyTheme(themePref() || 'light');

network.once('stabilizationIterationsDone', () => {
  network.setOptions({ physics: { enabled: false } });
});

function showInfo(nodeId) {
  const n = nodesDS.get(nodeId);
  if (!n) return;
  const neighborIds = network.getConnectedNodes(nodeId);
  const neighborItems = neighborIds.map(nid => {
    const nb = nodesDS.get(nid);
    const color = nb ? nb.color.background : '#555';
    return `<span class="neighbor-link" style="border-left-color:${esc(color)}" data-nid="${esc(nid)}">${esc(nb ? nb.label : nid)}</span>`;
  }).join('');
  const isMetaNode = !n.file_type && !n.source_file;
  let html = `<div class="field"><b>${esc(n.label)}</b></div>`;
  if (n.role) html += `<div class="field">${esc(n.role)}</div>`;
  if (!isMetaNode) {
    html += `<div class="field">Type: ${esc(n.file_type || 'unknown')}</div>`;
  }
  html += `<div class="field">Community: ${esc(n.community_name || '')}</div>`;
  if (!isMetaNode) {
    html += `<div class="field">Source: ${esc(n.source_file || '-')}</div>`;
  } else if (n.member_count !== undefined && n.member_count !== null) {
    html += `<div class="field">Members: ${esc(n.member_count)}</div>`;
  }
  html += `<div class="field">Degree: ${n.degree}</div>`;
  html += '<div class="field">' + esc(n.status) + '</div>';
  if (n.paper) html += '<a target="_top" href="/catalog/#' + encodeURIComponent(n.paper) + '">Read manuscript →</a>';
  if (neighborIds.length) {
    html += `<div class="field" style="margin-top:8px;color:var(--text-2);font-size:11px">Neighbors (${neighborIds.length})</div><div id="neighbors-list">${neighborItems}</div>`;
  }
  document.getElementById('info-content').innerHTML = html;
}

function focusNode(nodeId) {
  network.focus(nodeId, { scale: 1.4, animation: true });
  network.selectNodes([nodeId]);
  showInfo(nodeId);
}

// Neighbor links use a data attribute + one delegated listener rather than an
// inline onclick. A node id/label sourced from a document or a scraped URL
// (graphify add) can contain a double-quote; dropping the stringified id
// unescaped into a quoted onclick both broke every link and allowed a hostile
// source to inject an event handler into the local report (stored XSS, #1838).
// esc() on data-nid keeps the value inside the attribute; the listener reads it
// back verbatim. Bound to document so it survives the innerHTML rebuild that
// recreates #neighbors-list on each showInfo().
document.addEventListener('click', e => {
  const el = e.target.closest('.neighbor-link');
  if (el && el.dataset.nid !== undefined) focusNode(el.dataset.nid);
});


