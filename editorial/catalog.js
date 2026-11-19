import { element, link, links, readJSON, showRequestedAnchor } from './content.js';

const statusLabels = {
  journal: 'Published in journal',
  under_review: 'Under review',
  preprint: 'Archived preprint',
  published: 'Published',
  unpublished: 'Unpublished manuscript',
};

const typeLabels = {
  article: 'Journal article',
  report: 'Technical report',
  dataset: 'Dataset',
  preprint: 'Preprint',
  software: 'Software',
  manuscript: 'Manuscript',
  'defensive disclosure': 'Defensive disclosure',
};

const typeOrder = ['journal', 'under_review', 'preprint', 'published', 'unpublished'];

function publicationStatus(record) {
  if (record.historical) return 'Historical preprint';
  return statusLabels[record.status ?? record.type] ?? 'Archived record';
}

function verification(record) {
  if (record.verification) return record.verification;
  if (record.status === 'journal') return 'Journal peer review';
  if (record.type === 'preprint') return 'See the preprint for proof or validation details';
  return 'See source for verification details';
}

function recordAnchor(record) {
  return record.anchor ?? `doi-${record.doi.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
}

function metadata(rows) {
  const list = element('dl', '', 'record-facts');
  for (const [label, value] of rows) {
    if (!value) continue;
    const pair = element('div');
    pair.append(element('dt', label), element('dd', value));
    list.append(pair);
  }
  return list;
}

function publishLinks(record) {
  const sourceLinks = Array.isArray(record.links)
    ? record.links.map(item => typeof item === 'string' ? { label: 'Source', url: item } : item)
    : Object.entries(record.links ?? {}).map(([key, url]) => ({ label: key, url }));
  const doi = record.doi ? `https://doi.org/${record.doi}` : '';
  if (doi && !sourceLinks.some(item => item.url === doi)) {
    sourceLinks.push({ label: 'DOI', url: doi });
  }
  return links(sourceLinks);
}

function publicationCard(record, { featured, candidate, scale } = {}) {
  const card = element('article', '', featured ? 'record record-featured' : 'record');
  const id = recordAnchor(record);
  card.id = id;

  const title = element('h3');
  title.append(link(record.title, `#${id}`));
  const authors = Array.isArray(record.authors) ? record.authors.join(', ') : record.authors;
  const context = [authors || 'Oleg Dolgikh', record.date ?? record.year, record.venue].filter(Boolean);
  card.append(element('p', typeLabels[record.type] ?? record.type, 'eyebrow'), title,
    element('p', context.join(' · '), 'byline'));

  if (record.summary) card.append(element('p', record.summary, 'record-summary'));
  if (record.scope) card.append(element('p', record.scope, 'record-scope'));

  const facts = [
    ['Publication status', publicationStatus(record)],
    ['Verification', verification(record)],
    ['DOI', record.doi],
    ['Version', record.venue?.includes(`v${record.version}`) ? '' : record.version],
    ['License', record.license?.toUpperCase().replace(/-/g, ' ')],
  ];
  if (candidate) {
    facts.push(['Editorial readiness', `${record.readiness.score}/${scale}`],
      ['Editorial stage', record.readiness.stage]);
  }
  const sourceLinks = publishLinks(record);
  if (record.readiness && !candidate) {
    const candidateLink = element('li');
    candidateLink.append(link('Journal candidate', `/publications/#${id}`));
    sourceLinks.append(candidateLink);
  }
  card.append(metadata(facts), sourceLinks);
  if (candidate) {
    const next = element('p', '', 'next-step');
    next.append(element('strong', 'Next step'), ` ${record.readiness.next}`);
    card.append(next);
  }
  if (record.checksum) card.append(element('p', `Release archive SHA-256 ${record.checksum}`, 'checksum'));
  return card;
}

function sortRecords(records) {
  const position = record => {
    const index = typeOrder.indexOf(record.status ?? record.type);
    return index === -1 ? typeOrder.length : index;
  };
  return [...records].sort((a, b) => position(a) - position(b)
    || String(b.date ?? b.year ?? '').localeCompare(String(a.date ?? a.year ?? '')));
}

function renderCandidates(outlet, catalogue) {
  const { candidateGroups, publications, readinessScale } = catalogue;
  const nav = document.querySelector('[data-candidate-navigation]');
  const order = publications.filter(record => record.readiness).sort((a, b) => a.readiness.order - b.readiness.order);
  nav.replaceChildren();
  outlet.replaceChildren();
  for (const [group, name] of Object.entries(candidateGroups)) {
    nav.append(link(name, `#${group}`));
    const section = element('section', '', 'section');
    section.id = group;
    const title = element('h2', name);
    title.id = `${group}-title`;
    section.setAttribute('aria-labelledby', title.id);
    section.append(title);
    for (const record of order.filter(entry => entry.readiness.group === group)) {
      section.append(publicationCard(record, { candidate: true, scale: readinessScale }));
    }
    outlet.append(section);
  }
}

function searchableText(record) {
  return [record.title, record.authors, record.doi, record.summary].join(' ').toLowerCase();
}

function renderCatalogue(outlet, technical, records) {
  const search = document.getElementById('catalog-search');
  const count = document.getElementById('catalog-count');
  const render = () => {
    const query = search.value.toLowerCase().trim();
    const visible = records.filter(record => searchableText(record).includes(query));
    const researchRecords = visible.filter(record => record.collection !== 'technical');
    const technicalRecords = visible.filter(record => record.collection === 'technical');
    count.textContent = `${visible.length} ${visible.length === 1 ? 'record' : 'records'}`;
    outlet.replaceChildren(...researchRecords.map(record => publicationCard(record)));
    technical.replaceChildren(...technicalRecords.map(record => publicationCard(record)));
    document.getElementById('defensivePublications').hidden = !technicalRecords.length;
    if (!visible.length) outlet.append(element('p', 'No records match your search.'));
  };
  search.disabled = false;
  search.addEventListener('input', render);
  render();
}

try {
  const catalogue = await readJSON('/publications.json');
  const sorted = sortRecords(catalogue.publications);
  for (const outlet of document.querySelectorAll('[data-catalog-view]')) {
    const { catalogView, program } = outlet.dataset;
    if (catalogView === 'candidates') renderCandidates(outlet, catalogue);
    if (catalogView === 'all') renderCatalogue(outlet, document.querySelector('[data-catalog-view=technical]'), sorted);
    if (program) {
      const featured = catalogView === 'featured';
      const selected = sorted.filter(record => record.program === program && Boolean(record.featured) === featured);
      outlet.replaceChildren(...selected.map(record => publicationCard(record, { featured })));
    }
  }
  showRequestedAnchor();
} catch (error) {
  console.error('Catalogue unavailable', error);
  for (const outlet of document.querySelectorAll('[data-catalog-view]')) {
    outlet.replaceChildren(element('p', 'The catalogue could not be loaded. Refresh the page to try again.'));
  }
}
