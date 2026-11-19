const canvas = document.getElementById('dephasing-chart');
const context = canvas.getContext('2d');
const rows = [...document.querySelectorAll('#dephasing-data tbody tr')];

if (context) {
  const styles = getComputedStyle(canvas);
  const color = name => styles.getPropertyValue(name).trim();
  const scale = styles.getPropertyValue('--chart-scale').trim().split(' ').map(Number);
  const chartBox = { left: 70, right: 685, top: 26, bottom: 298 };
  const { left, right, top, bottom } = chartBox;
  const width = right - left;
  const height = bottom - top;
  const max = Math.max(...scale);
  const y = value => bottom - (value / max) * height;

  context.font = color('--chart-type') + ' system-ui';
  context.textBaseline = 'middle';
  context.textAlign = 'right';
  for (const tick of scale) {
    context.strokeStyle = color('--figure-grid');
    context.beginPath();
    context.moveTo(left, y(tick));
    context.lineTo(right, y(tick));
    context.stroke();
    context.fillStyle = color('--figure-muted');
    context.fillText(tick, left - 13, y(tick));
  }

  const step = width / rows.length;
  rows.forEach((row, index) => {
    const [label, value] = [...row.cells].map(cell => cell.textContent);
    const x = left + step * (index + 0.5);
    const barWidth = step * 0.48;
    context.fillStyle = color(index === 0 ? '--figure-highlight' : '--figure-bar');
    context.fillRect(x - barWidth / 2, y(Number(value)), barWidth, bottom - y(Number(value)));
    context.fillStyle = color('--figure-text');
    context.textAlign = 'center';
    context.fillText(Number(value).toFixed(3), x, y(Number(value)) - 15);
    context.fillText(label, x, bottom + 28);
  });
  context.fillStyle = color('--figure-muted');
  context.fillText('Dephasing rate κ', left + width / 2, 371);
}
