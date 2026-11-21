// All curator choices, text, and visual values come from findings.json.
(() => {
  const config = window.atlasFindings;
  const entries = new Map(Object.entries(config.entries));
  if (!entries.size) return;
  const style = config.style;
  document.documentElement.style.setProperty('--finding-accent', style.accent);
  let onlyFindings = false;
  let updating = false;

  const panel = document.createElement('section');
  panel.id = 'findings-panel';
  panel.setAttribute('aria-label', 'Potential findings');
  panel.innerHTML = `<button type="button" id="findings-toggle" aria-pressed="false" aria-controls="findings-list">
    <span class="finding-mark">${'◯'}</span> ${esc('Potential findings')} (${entries.size})</button>
    <p><span class="finding-mark">${'◯'}</span> ${esc('Gold rings mark research potential. Novelty and verification are assessed separately.')}</p>
    <div id="findings-list" hidden></div>`;
  document.querySelector('#search-wrap').before(panel);
  const button = panel.querySelector('#findings-toggle');
  const list = panel.querySelector('#findings-list');

  // Compose with stock status/type/community filters, including Select All.
  function syncVisibility() {
    if (updating) return;
    const updates = RAW_NODES.map(node => ({
      id: node.id,
      hidden: hiddenCommunities.has(node.community) || (onlyFindings && !entries.has(node.id)),
    })).filter(node => Boolean(nodesDS.get(node.id).hidden) !== node.hidden);
    if (updates.length) {
      updating = true;
      nodesDS.update(updates);
      updating = false;
    }
  }
  nodesDS.on('update', syncVisibility);
  button.addEventListener('click', () => {
    onlyFindings = !onlyFindings;
    button.setAttribute('aria-pressed', String(onlyFindings));
    list.hidden = !onlyFindings;
    syncVisibility();
    const visible = nodesDS.get().filter(node => !node.hidden).map(node => node.id);
    if (visible.length) network.fit({nodes: visible, animation: false});
  });

  for (const [id, entry] of entries) {
    const link = document.createElement('button');
    link.type = 'button';
    link.className = 'finding-link';
    link.dataset.findingId = id;
    link.innerHTML = `<span class="finding-mark">${'◯'}</span> ${esc(nodesDS.get(id).label)}`;
    link.addEventListener('click', () => {
      const node = nodesDS.get(id);
      if (hiddenCommunities.has(node.community)) {
        const index = LEGEND.findIndex(group => group.cid === node.community);
        const checkbox = document.querySelectorAll('.legend-cb')[index];
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change'));
      }
      syncVisibility();
      network.selectNodes([id]);
      if (!nodesDS.get(id).hidden) network.focus(id, {scale: 1.3, animation: false});
      showInfo(id);
      document.querySelector('#info-panel').scrollTop = 0;
    });
    list.appendChild(link);
  }

  const originalShowInfo = showInfo;
  showInfo = function (id) {
    originalShowInfo(id);
    const entry = entries.get(id);
    if (!entry) return;
    const card = document.createElement('section');
    card.className = 'finding-card';
    card.innerHTML = `<h4><span class="finding-mark">${'◯'}</span> ${esc('Potential finding')}</h4><dl>${Object.entries({significance:"Scientific significance",scientific_verification:"Verification",novelty:"Novelty",publication_readiness:"Publication"}).filter(([key]) => entry[key])
      .map(([key, label]) => `<dt>${esc(label)}</dt><dd>${esc(entry[key])}</dd>`).join('')}</dl>`;
    if (entry.doi) {
      const link = document.createElement('a');
      link.href = 'https://doi.org/' + entry.doi;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = 'Preprint · ' + entry.doi;
      card.append(link);
    }
    document.querySelector('#info-content').prepend(card);
  };

  // Draw an independent outer ring: status fill, label, search, and selection stay intact.
  network.on('afterDrawing', ctx => {
    for (const id of entries.keys()) {
      const node = nodesDS.get(id);
      if (!node || node.hidden) continue;
      const point = network.getPosition(id);
      ctx.save();
      ctx.strokeStyle = style.accent;
      ctx.lineWidth = style.ring_width;
      ctx.shadowColor = style.accent;
      ctx.shadowBlur = style.halo_blur;
      ctx.beginPath();
      ctx.arc(point.x, point.y, node.size + style.ring_gap, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.restore();
    }
  });
  network.redraw();
  if (requestedNode && entries.has(requestedNode)) showInfo(requestedNode);
  if (location.hash === '#findings') button.click();
})();
