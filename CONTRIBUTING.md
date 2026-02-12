# 🧪 How to Add a New Organism Page

> **Difficulty level:** Copy–paste + fill in the blanks.  
> **Time needed:** ~15 minutes.  
> **Skills needed:** Basic text editor. No coding required.

---

## Overview

This site is a collection of standalone HTML pages — one per organism/pathway.  
Each page is a single file with everything inside (CSS, JS, data).  
To add a new page, you **copy a template, fill in your data, and register it**.

```
your-repo/
├── index.html          ← Hub page (auto-reads pages.json)
├── pages.json          ← Registry: one entry per organism
├── human.html          ← Example: full GKSL animation
├── drosophila.html     ← Example: static connectome
├── TEMPLATE.html       ← ★ Start here ★
└── CONTRIBUTING.md     ← This file
```

---

## Step-by-step guide

### Step 0 — Get the template

1. Download or open `TEMPLATE.html` in any text editor  
   (VS Code, Notepad++, TextEdit — anything works).
2. **Save it** with your organism name, e.g. `elegans.html` or `mouse.html`.

### Step 1 — Change the page title

Find this line near the top:

```html
<title>YOUR ORGANISM NAME — YOUR PATHWAY | CRN Interactive</title>
```

Replace it, for example:

```html
<title>C. elegans — Touch Circuit | CRN Interactive</title>
```

### Step 2 — Fill in the hero section

Look for the big comment box that says **STEP 2**. You'll see:

```html
<h1>YOUR_MAIN_TITLE</h1>
```

Replace with your actual title and subtitle:

```html
<div class="hero-eyebrow"><span class="dot"></span>Model Organism</div>
<h1>C. elegans Touch Withdrawal Circuit</h1>
<p class="hero-sub">Minimal connectome benchmark: 24 neurons from
mechanosensory input to motor command.</p>
```

### Step 3 — Fill in the stat cards

Each stat card has 4 rows. Just change the text and numbers:

```html
<div class="stat-row">
  <span class="stat-label">Nodes</span>
  <span class="stat-val">24</span>   ← your number here
</div>
```

**Color hints** for values:
- `class="stat-val good"` → green (for positive results, ✓)
- `class="stat-val warn"` → amber (for key numbers)
- `class="stat-val bad"` → red (for negative results, ✗)
- `class="stat-val"` → neutral (default)

### Step 4 — Add your graph data

Find the `<script>` section at the bottom. Replace the example nodes and edges
with your actual data:

```javascript
const nodes = [
  {id: 0, type: 'source', x: 0, y: 0},  // Sensory neuron
  {id: 1, type: 'inter',  x: 0, y: 0},  // Interneuron
  {id: 2, type: 'target', x: 0, y: 0},  // Motor neuron
  // ... add all your nodes
];

const edges = [
  {source: 0, target: 1},  // Sensory → Inter
  {source: 1, target: 2},  // Inter → Motor
  // ... add all your edges
];
```

**Node types** and their colors:
| `type` value | Color | Typical use |
|---|---|---|
| `'source'` | Indigo (●) | Input / sensory nodes |
| `'target'` | Amber (●) | Output / decision nodes |
| `'inter'` | Teal (●) | Everything else |

The layout engine (hierarchical / force / circular) positions them automatically.
You don't need to set x/y manually.

### Step 5 — Fill in the source citation

```html
<div class="source-box">
  <strong>Data source:</strong> White et al. (1986). <em>The structure of
  the nervous system of C. elegans.</em> Phil. Trans. R. Soc. Lond. B.
  <a href="https://doi.org/..." target="_blank">doi:...</a><br>
  <strong>CRN framework:</strong> Dolgikh (2026).
  <a href="https://doi.org/10.5281/zenodo.18249250">doi:...</a>
</div>
```

### Step 6 — Register the page

Open `pages.json` and add a new entry:

```json
{
  "id": "elegans",
  "title": "C. elegans — Touch Circuit",
  "desc": "Minimal connectome benchmark. Touch → command → motor. N=24.",
  "date": "2026-02-15",
  "tags": ["nematode", "minimal", "DES"]
}
```

**Important:** the `"id"` must match your filename without `.html`.  
So `"id": "elegans"` → the file must be `elegans.html`.

### Step 7 — (Optional) Add an icon

In `index.html`, find the `icons` object and add your emoji:

```javascript
const icons = {
  human:     {emoji:'🧠', bg:'var(--accent-light)'},
  drosophila:{emoji:'🪰', bg:'var(--teal-light)'},
  elegans:   {emoji:'🪱', bg:'var(--warm-light)'},    // ← add this
  mouse:     {emoji:'🐭', bg:'var(--coral-light)'},   // ← add this
};
```

If you skip this step, a default 📊 icon is used.

### Step 8 — Test locally

Option A (simplest): Just open `index.html` in your browser.  
Cards are loaded from `pages.json` — this requires a local server:

```bash
# In your repo folder, run:
python -m http.server 8000

# Then open http://localhost:8000
```

Option B: Open your `elegans.html` file directly — it works standalone.

### Step 9 — Push to GitHub

```bash
git add elegans.html pages.json
git commit -m "Add C. elegans touch circuit page"
git push
```

If GitHub Pages is enabled, your page will be live in ~1 minute.

---

## Dark mode

All pages support dark/light mode automatically. The toggle button (🌙/☀️) is
in the top-right corner. The user's preference is saved in localStorage.

You don't need to do anything — it just works because all colors use CSS
variables that switch between light and dark values.

---

## Advanced: Adding GKSL trajectory animation

If you have trajectory data (generated by `crn_dump_trajectories.py`), you can
upgrade from a static graph to an animated visualization like `human.html`.

1. Run the trajectory generator:
   ```bash
   python crn_dump_trajectories.py \
     --graphml your_graph.graphml \
     --subject YOUR_ID \
     --port YOUR_PORT \
     --outfile trajectories_output.json
   ```

2. Copy the animation code from `human.html` (the `<script>` section).

3. Replace `const TRAJ = {...}` with the contents of your JSON file.

4. Update the `NODES` array with your node coordinates and roles.

This is more complex — ask for help if needed.

---

## File checklist

Before pushing, verify:

- [ ] Your `.html` file opens correctly in browser
- [ ] Dark mode toggle works (click 🌙 in top-right)
- [ ] All stat card numbers are filled in (no "NUMBER" placeholders left)
- [ ] Source citation is complete with DOI link
- [ ] `pages.json` has your new entry
- [ ] `"id"` in `pages.json` matches your filename (without `.html`)

---

## Questions?

Open an issue on GitHub or contact the maintainer.
