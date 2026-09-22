// Keep the data readable without JavaScript; enhance only the presentation.
document.querySelectorAll('[data-busy-form]').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = button.dataset.busyLabel;
    const status = form.querySelector('[data-form-status]');
    status.textContent = status.dataset.busyMessage || 'Retrieving observations. Please keep this page open.';
  });
});
const trend = document.getElementById('forecast-trend');
if (trend) {
  const cards = [...document.querySelectorAll('[data-temperature]')];
  const values = cards.map(card => Number(card.dataset.temperature));
  if (values.length && values.every(Number.isFinite)) {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 800 220');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Predicted daily mean temperature trend. Exact dates and temperatures are listed above.');
    const add = (tag, attrs, text) => {
      const element = document.createElementNS(ns, tag);
      Object.entries(attrs).forEach(([key,value]) => element.setAttribute(key, value));
      if (text !== undefined) element.textContent = text;
      svg.appendChild(element);
      return element;
    };
    const min = Math.min(...values) - 3, max = Math.max(...values) + 3;
    const points = values.map((value, i) => [60 + i * 680 / Math.max(values.length - 1, 1), 170 - (value - min) / (max - min) * 140]);
    for(let i=0; i<4; i++) {
      const y = 30 + i * 140 / 3;
      add('line', {x1:55,y1:y,x2:750,y2:y,stroke:'#e5eeeb'});
      add('text', {x:45,y:y+4,'text-anchor':'end',fill:'#617777','font-size':12}, `${(max-i*(max-min)/3).toFixed(0)}°`);
    }
    add('polygon', {points:`${points[0][0]},170 ${points.map(p=>p.join(',')).join(' ')} ${points.at(-1)[0]},170`,fill:'#e4efe5'});
    add('polyline', {points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#176d61','stroke-width':3,'stroke-linejoin':'round'});
    points.forEach(([x,y],i) => {
      const dot=add('circle',{cx:x,cy:y,r:5,fill:'#fff',stroke:'#176d61','stroke-width':2});
      const title=document.createElementNS(ns,'title');
      title.textContent=`${cards[i].dataset.day}: ${values[i].toFixed(1)} °F`;
      dot.appendChild(title);
      add('text',{x,y:203,'text-anchor':'middle',fill:'#617777','font-size':11},cards[i].dataset.day);
    });
    trend.appendChild(svg);
  }
}
