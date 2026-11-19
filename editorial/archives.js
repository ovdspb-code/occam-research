import { element, link, links, readJSON, showRequestedAnchor } from './content.js';

function renderCompanions(outlet, pages) {
  const cards = pages.map(page => {
    const card = element('article');
    const title = element('h3');
    title.append(link(page.title, `/${page.id}.html`));
    card.append(title, element('p', page.desc));
    return card;
  });
  outlet.replaceChildren(...cards);
}

function renderScorecard(outlet, data) {
  const list = element('div', '', 'scorecard-list');
  for (const claim of data.claims) {
    const entry = element('article');
    entry.append(element('h3', `${claim.name} · ${claim.score}%`),
      element('p', claim.desc), element('p', claim.evidence), element('p', claim.gap));
    list.append(entry);
  }
  outlet.replaceChildren(element('p', data.note), list);
}

function renderDuels(outlet, data) {
  const series = element('p');
  if (data.doi) series.append(link('Series archive', `https://doi.org/${data.doi}`));
  const entries = [...data.disputes].sort((a, b) => b.date.localeCompare(a.date)).map(issue => {
    const card = element('article', '', 'record');
    const title = element('h3');
    title.append(link(issue.title, `/${issue.html}`));
    const sources = [
      { label: 'Read issue', url: `/${issue.html}` },
      { label: 'PDF', url: issue.pdf && `/${issue.pdf}` },
      { label: 'Archived PDF', url: issue.archived_pdf },
      { label: 'DOI', url: issue.doi && `https://doi.org/${issue.doi}` },
    ];
    card.append(element('p', `Issue ${issue.no} · ${issue.date}`, 'eyebrow'), title,
      element('p', issue.subtitle));
    if (issue.verdict) {
      const details = element('details');
      details.append(element('summary', 'Verdict'), element('p', issue.verdict));
      card.append(details);
    }
    card.append(links(sources));
    return card;
  });
  outlet.replaceChildren(series, ...entries);
}

const archives = [
  ['[data-crn-pages]', '/pages.json', renderCompanions, 'The interactive companion list could not be loaded.'],
  ['[data-scorecard]', '/scorecard.json', renderScorecard, 'The historical scorecard could not be loaded.'],
  ['[data-duels]', '/disputes.json', renderDuels, 'The issue archive could not be loaded.'],
];

await Promise.all(archives.map(async ([selector, path, render, fallback]) => {
  const outlet = document.querySelector(selector);
  if (!outlet) return;
  try {
    render(outlet, await readJSON(path));
  } catch (error) {
    console.error('Archive unavailable', error);
    outlet.replaceChildren(element('p', fallback), link('Source file', path));
  }
}));
if (location.hash === '#scorecardGrid') {
  const scorecard = document.getElementById('scorecardGrid');
  if (scorecard) scorecard.open = true;
}
if (['#scorecardSection', '#scorecardGrid', '#workSection', '#cardGrid', '#disputesList'].includes(location.hash)) {
  showRequestedAnchor();
}
