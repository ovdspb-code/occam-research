# Occam Research — research portfolio and CRN companions

Public research portfolio of Oleg Dolgikh / Occam Research: publications, preprints, reproducible resources, and interactive companions for **Coherent Resonant Netting**.

**Live site:** https://occam.world

**Author:** Oleg Dolgikh · Independent Researcher · [ORCID](https://orcid.org/0009-0008-0159-1718)

**Bibliography:** [Google Scholar](https://scholar.google.com/citations?user=6wxP_EkAAAAJ&hl=en). The owner profile was verified on 2026-10-02; profile entries and search indexing are separate states.

The catalogue distinguishes journal articles, preprints, datasets, software, and explanatory materials. Publication on an archive does not imply journal peer review.

## Pages

| Organism | Pathway | Status |
|---|---|---|
| 🧠 Human | Basal ganglia (T2) / Motor relay (T3) | ✅ Live |
| 🪰 Drosophila | Mushroom body (PN→KC→MBON) | ✅ Live |
| 🪱 C. elegans | Touch circuit | [Page](https://occam.world/elegans.html) |
| 🐭 Mouse | Synthetic cortex proxy | [Page](https://occam.world/mouse.html) |

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

- Dolgikh (2026). *Coherent-resonant netting: disorder-enhanced selectivity from transient wave-like dynamics on biological connectomes.* Frontiers in Computational Neuroscience. [doi:10.3389/fncom.2026.1813959](https://doi.org/10.3389/fncom.2026.1813959)

- Dolgikh (2026). *CRN Framework.* [doi:10.5281/zenodo.18249250](https://doi.org/10.5281/zenodo.18249250)
- [CRN Simulation Code](https://github.com/ovdspb-code/CRN_4.1)
