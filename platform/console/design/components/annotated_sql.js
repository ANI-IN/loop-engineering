export default function (component) {
  const { parentElement: root, data } = component;
  const p = probe('annotated_sql');
  p.calls++;
  if (!root.__dp) { root.__dp = { instance: rid() }; p.mounts++; root.querySelector('.asql').dataset.instance = root.__dp.instance; }
  const key = JSON.stringify(data);
  if (root.__dp.key === key) return () => { p.cleanups++; };
  root.__dp.key = key;
  const head = root.querySelector('.head'); head.replaceChildren();
  if (data.stamp) head.append(stampLine(data.stamp, data.display_tz, 'Open trace in LangSmith'));
  const code = root.querySelector('.code'); code.replaceChildren();
  data.lines.forEach((text, i) => {
    const row = el('div', 'ln'); const tx = el('span', 'tx');
    const marks = data.marks.filter((m) => m.line === i).sort((a, b) => a.start - b.start);
    let at = 0;
    for (const m of marks) {
      tx.append(document.createTextNode(text.slice(at, m.start)));
      const mk = el('mark', '', text.slice(m.start, m.end));
      mk.setAttribute('aria-describedby', `note-${m.n}`);
      tx.append(mk, el('sup', 'tag', m.n));
      at = m.end;
    }
    tx.append(document.createTextNode(text.slice(at)));
    row.append(el('span', 'no', i + 1), tx);
    code.append(row);
  });
  const notes = root.querySelector('.notes'); notes.replaceChildren();
  for (const n of data.notes) {
    const li = el('li'); li.id = `note-${n.n}`;
    li.append(el('span', 'n', n.n), el('span', 'trap', `Trap: ${n.trap}`), el('span', 'txt', n.text));
    notes.append(li);
  }
  root.querySelector('.clean').hidden = data.notes.length > 0;
  notes.hidden = data.notes.length === 0;
  return () => { p.cleanups++; };
}
