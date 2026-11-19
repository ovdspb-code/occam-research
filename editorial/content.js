export async function readJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${path}`);
  return response.json();
}

export function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

export function link(label, url) {
  const anchor = element('a', label);
  const target = new URL(url, location.href);
  if (['http:', 'https:'].includes(target.protocol)) {
    anchor.href = target.origin === 'https://occam.world'
      ? target.pathname + target.search + target.hash
      : target.href;
  }
  return anchor;
}

export function links(items) {
  const row = element('ul', '', 'record-links');
  for (const { label, url } of items) {
    if (!url) continue;
    const item = element('li');
    item.append(link(label ?? 'Source', url));
    row.append(item);
  }
  return row;
}

export function showRequestedAnchor() {
  const id = location.hash.slice(1);
  if (id) document.getElementById(decodeURIComponent(id))?.scrollIntoView();
}
