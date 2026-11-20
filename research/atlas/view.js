import {element, readJSON} from '/editorial/content.js';

const outlet = document.querySelector('[data-atlas]');
const slug = name => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-$/, '');

async function render() {
  const [books, catalogue] = await Promise.all([readJSON('/research/atlas/topics.json'), readJSON('/publications.json')]);
  const topics = books[outlet.dataset.atlas];
  const manuscripts = new Map(catalogue.publications.map(record => [record.anchor, record]));
  const index = element('nav', '', 'topic-index');
  index.setAttribute('aria-label', 'Atlas topics');
  const detail = element('section', '', 'topic-detail');
  const heading = element('h2');
  heading.tabIndex = -1;
  const controls = new Map();
  const furtherReading = {
    'Learning after a change': ['directed-structural-drift', 'joint-training'],
    'Acquired compatibility': ['work-induced-specialization'],
    'Smaller physical models': ['minimum-network-size'],
    'Networks in combination': ['structural-safety'],
  };
  function topicLink(name, label) {
    const a = element('a', label);
    a.href = '#' + slug(name);
    return a;
  }
  topics.forEach(topic => {
    const a = topicLink(topic.name, topic.name);
    controls.set(topic, a);
    index.append(a);
  });
  function select(moveFocus = false) {
    const topic = topics.find(t => '#' + slug(t.name) === location.hash) || topics[0];
    controls.forEach((control, t) => {
      if (t === topic) control.setAttribute('aria-current', 'true');
      else control.removeAttribute('aria-current');
    });
    heading.textContent = topic.name;
    const question = element('p', topic.question, 'topic-question');
    const items = element('ul', '', 'atlas-entries');
    for (const entry of topic.selected) {
      const row = element('li');
      row.append(element('small', entry.status), element('strong', entry.title));
      const paper = manuscripts.get(entry.paper);
      if (paper) {
        const a = element('a', paper.title);
        a.href = '/catalog/#' + paper.anchor;
        row.append(a);
      }
      items.append(row);
    }
    detail.replaceChildren(heading, question, element('h3','Selected entries'), items);
    const related = (furtherReading[topic.name] || []).map(anchor => manuscripts.get(anchor)).filter(Boolean);
    if (related.length) {
      const reading = element('ul');
      for (const paper of related) {
        const row = element('li');
        const a = element('a', paper.title);
        a.href = '/catalog/#' + paper.anchor;
        row.append(a);
        reading.append(row);
      }
      detail.append(element('h3', 'Related manuscripts'), reading);
    }
    const relations = Object.entries(topic.links).sort((a,b) => b[1]-a[1]);
    if (relations.length) {
      const list = element('ul', '', 'atlas-relations');
      for (const [name, count] of relations) {
        const row = element('li');
        const a = topicLink(name, name);
        a.append(element('span', String(count)));
        a.setAttribute('aria-label', name + ', ' + count + ' cross-topic links');
        a.style.setProperty('--share', (100 * count / relations[0][1]) + '%');
        row.append(a);
        list.append(row);
      }
      detail.append(element('h3','Connections to other topics'), element('p',
        'This topic contains ' + topic.entries + ' atlas entries. The counts below show links to entries in other topics.'), list);
    }
    if (moveFocus) heading.focus();
  }
  outlet.replaceChildren(index, detail);
  select(Boolean(location.hash));
  window.addEventListener('hashchange', () => select(true));
}
render().catch(() => { outlet.textContent = 'The atlas could not be loaded. Reload this page to try again.'; });
