// All alternatives share one grid cell so wrapping follows the reader's font and viewport.
export function stableText(host, value, alternatives) {
 const layer = document.createElement('span');
 layer.className = 'text-layers';
 for (const alternative of new Set(alternatives)) {
  const measure = document.createElement('span');
  measure.setAttribute('aria-hidden', 'true');
  measure.textContent = alternative;
  layer.append(measure);
 }
 const visible = document.createElement('span');
 visible.textContent = value;
 layer.append(visible);
 host.replaceChildren(layer);
}
