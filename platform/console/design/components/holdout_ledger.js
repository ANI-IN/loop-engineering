function cell(v, cls) {
  if (!v || v.pending) {
    const c = el('span', `cell pending ${cls}`);
    c.append(el('span', 'mark hollow'), el('span', 'b', 'Not run yet'));
    return c;
  }
  const c = el('span', `cell ${v.passed ? 'pass' : 'fail'} ${cls}`);
  c.append(el('span', 'mark ' + (v.passed ? 'filled' : 'cross')),
           el('span', 'b', v.passed ? 'Passed' : 'Failed'), el('span', 'runs', v.runs));
  return c;
}
const CHANGE = { fixed: 'Fixed: now passes', regression: 'Regression', same: 'No change' };
export default function (component) {
  const { parentElement: root, data } = component;
  const p = probe('holdout_ledger');
  p.calls++;
  if (!root.__dp) {
    root.__dp = { instance: rid() }; p.mounts++;
    root.querySelector('.ledger').dataset.instance = root.__dp.instance;
    root.querySelector('.start')
      .addEventListener('click', () => root.__dp.trigger('start_baseline', Date.now()));
  }
  root.__dp.trigger = component.setTriggerValue;
  const key = JSON.stringify(data);
  if (root.__dp.key === key) return () => { p.cleanups++; };
  root.__dp.key = key;
  const ledger = root.querySelector('.ledger');
  // collapsed: the grouped benchmark strip is closed, so the ledger takes no space.
  ledger.classList.toggle('collapsed', data.state === 'collapsed');
  const live = data.state === 'live';
  root.querySelector('.live').hidden = !live;
  root.querySelector('.nobase').hidden = data.state !== 'no_baseline';
  if (!live) return () => { p.cleanups++; };
  const single = !data.candidate_version;
  ledger.classList.toggle('single', single);
  const stamps = root.querySelector('.stamps'); stamps.replaceChildren();
  const experiments = [['Baseline, ' + data.active_label, data.baseline_stamp]];
  if (!single) experiments.push(['Candidate, ' + data.candidate_version, data.candidate_stamp]);
  for (const [name, stamp] of experiments) {
    stamps.append(el('span', 'k', name), stampLine(stamp, data.display_tz));
  }
  root.querySelector('.sum').textContent = data.summary_text;
  root.querySelector('.ah').textContent = data.active_label;
  root.querySelector('.ch').textContent = data.candidate_label || '';
  const rows = root.querySelector('.rows'); rows.replaceChildren();
  for (const r of data.rows) {
    const row = el('div', 'row r ' + r.change);
    row.setAttribute('aria-label', `${r.item}, ${CHANGE[r.change] || 'not run yet'}`);
    row.title = r.item;
    row.append(el('span', 'q', r.question), cell(r.active, 'act'), cell(r.candidate, 'cand'),
               el('span', 'chg ' + r.change, CHANGE[r.change] || ''),
               r.trace_url ? link(r.trace_url, 'Trace') : el('span', 'k', 'None'));
    rows.append(row);
  }
  const list = root.querySelector('.list');
  list.replaceChildren();
  if (data.trace_list_url) {
    const version = data.candidate_version || 'v1';
    list.append(link(data.trace_list_url, `Open every ${version} trace in LangSmith`),
                document.createTextNode(', filtered by knowledge version.'));
  }
  return () => { p.cleanups++; };
}
