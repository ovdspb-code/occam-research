"""Draw the weighted touch-circuit plate from the website companion's edge list."""
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = (ROOT / 'elegans-data.js').read_text()
nodes = re.findall(r"\{name:'(\w+)',type:'\w+'\}", data.split('const EDGES')[0])
edges = json.loads(re.search(r'const EDGES = (\[.*?\]);', data).group(1))
center = 250
radius = 174
angles = [2 * math.pi * i / len(nodes) - math.pi / 2 for i in range(len(nodes))]
navy, crimson = '#203953', '#a53658'


def point(angle, distance):
    return center + distance * math.cos(angle), center + distance * math.sin(angle)


pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">']
for source, target, weight in edges:
    start, end = point(angles[source], radius), point(angles[target], radius)
    a, b = point(angles[source], radius * .46), point(angles[target], radius * .46)
    selected = 'AVA' in (nodes[source], nodes[target])
    pieces.append(f'<path d="M {start[0]} {start[1]} C {a[0]} {a[1]}, {b[0]} {b[1]}, {end[0]} {end[1]}" fill="none" stroke="{crimson if selected else navy}" stroke-opacity="{.9 if selected else .46}" stroke-width="{weight * .8}"/>')
for i, name in enumerate(nodes):
    angle = angles[i]
    x, y = point(angle, radius)
    tx, ty = point(angle, radius + 13)
    anchor = 'start' if math.cos(angle) > .15 else 'end' if math.cos(angle) < -.15 else 'middle'
    color = crimson if name == 'AVA' else navy
    pieces.append(f'<circle cx="{x}" cy="{y}" r="3.3" fill="{color}"/>')
    pieces.append(f'<text x="{tx}" y="{ty+4}" text-anchor="{anchor}" fill="{color}" font-family="monospace" font-size="13">{name}</text>')
pieces.append('</svg>')
subprocess.run(['cairosvg', '-', '--scale', '2', '-o', str(ROOT / 'editorial/touch-circuit.png')], input=''.join(pieces), text=True, check=True)
