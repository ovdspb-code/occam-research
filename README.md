# CRN Interactive — Occam Research

Interactive visualizations of **Coherent Resonant Netting** dynamics across biological connectomes.

🌐 **Live site:** [GitHub Pages link]

## Pages

| Organism | Pathway | Status |
|---|---|---|
| 🧠 Human | Basal ganglia (T2) / Motor relay (T3) | ✅ Live |
| 🪰 Drosophila | Mushroom body (PN→KC→MBON) | ✅ Live |
| 🪱 C. elegans | Touch circuit | 🔜 Coming |
| 🐭 Mouse | Cortex proxy | 🔜 Coming |

## Adding a new page

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for a step-by-step guide.

Quick summary:
1. Copy `TEMPLATE.html` → `your_organism.html`
2. Fill in the 6 marked sections (title, hero, stats, data, citation)
3. Add an entry to `pages.json`
4. Push to GitHub

## Tech

- Pure HTML + CSS + vanilla JS (no build tools, no frameworks)
- Each page is fully self-contained (~20–100 KB)
- Dark/light mode with system preference detection
- Works offline, deploys to any static host

## References

- Dolgikh (2026). *CRN Framework.* [doi:10.5281/zenodo.18249250](https://doi.org/10.5281/zenodo.18249250)
- [CRN Simulation Code](https://github.com/ovdspb-code/CRN_4.1)
