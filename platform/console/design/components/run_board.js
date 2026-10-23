function fillStrip(node, s, tz) {
  node.className = 'strip ' + s.edge;
  node.setAttribute('aria-label', `${s.label}, ${s.word}`);
  const parts = [el('div', 'word ' + s.edge, s.word), el('div', 'q', s.question)];
  if (s.kind === 'benchmark') {
    // One grouped strip per running benchmark; its runs never appear as strips of their own.
    const bar = el('div', 'progress');
    const fill = el('span');
    fill.style.width = `${Math.round((100 * s.done) / s.total)}%`;
    bar.append(fill);
    bar.setAttribute('aria-hidden', 'true');
    parts.push(bar);
  }
  if (s.step) parts.push(el('div', 'step', s.step));
  parts.push(stampLine(s.stamp, tz));
  if (s.duplicates) {
    parts.push(el('div', 'dups',
      `${s.duplicates} duplicate${s.duplicates === 1 ? '' : 's'} absorbed`));
  }
  if (s.review) {
    const b = el('button', 'review', 'Review');
    b.type = 'button'; b.dataset.review = s.run_id;
    parts.push(b);
  }
  if (s.kind === 'benchmark') {
    const b = el('button', 'expand', s.expanded ? 'Hide holdout ledger' : 'Show holdout ledger');
    b.type = 'button'; b.dataset.expand = s.run_id;
    b.setAttribute('aria-expanded', String(!!s.expanded));
    parts.push(b);
  }
  node.replaceChildren(...parts);
}
export default function (component) {
  const { parentElement: root, data } = component;
  const p = probe('run_board');
  p.calls++;
  let st = root.__dp;
  if (!st) {
    st = root.__dp = {
      instance: rid(), strips: new Map(), lists: {}, counts: {}, mores: {}, lastKey: {},
    };
    p.mounts++;
    const board = root.querySelector('.board');
    board.dataset.instance = st.instance;
    const add = (parent, cls, head, item) => {
      const col = el('div', cls); const h = el(head); const count = el('span', 'count');
      h.append(el('span', '', item.title), count);
      const list = el('div', 'list'); list.dataset.lane = item.id;
      const more = el('div', 'more');
      list.append(more); col.append(h, list); parent.append(col);
      st.lists[item.id] = list; st.counts[item.id] = count; st.mores[item.id] = more;
    };
    for (const lane of data.lanes) add(root.querySelector('.lanes'), 'lane', 'h3', lane);
    for (const bay of data.off) add(root.querySelector('.off'), 'bay', 'h4', bay);
    board.addEventListener('click', (e) => {
      const review = e.target.closest('button[data-review]');
      if (review) st.trigger('review', review.dataset.review);
      const expand = e.target.closest('button[data-expand]');
      if (expand) st.trigger('toggle_ledger', expand.dataset.expand);
    });
  }
  st.trigger = component.setTriggerValue;

  const seen = new Set();
  const perLane = {};
  const bays = new Set(data.off.map((b) => b.id));
  // console.strips_per_lane from pack.yaml; a bay off the board shows only its newest strip.
  const limitFor = (id) => (bays.has(id) ? 1 : data.per_lane);
  // Newest first inside each lane: the data lists runs oldest first.
  for (const s of [...data.strips].reverse()) {
    seen.add(s.run_id);
    let node = st.strips.get(s.run_id);
    if (!node) {
      node = el('article', 'strip'); node.dataset.run = s.run_id;
      st.strips.set(s.run_id, node);
    }
    const key = JSON.stringify([s, data.display_tz]);
    if (st.lastKey[s.run_id] !== key) fillStrip(node, s, data.display_tz);
    const list = st.lists[s.lane];
    const moved = node.parentElement !== list;
    const index = (perLane[s.lane] = (perLane[s.lane] || 0) + 1);
    node.hidden = index > limitFor(s.lane);
    // Keep DOM order equal to data order without detaching nodes that are already in place.
    const anchor = st.mores[s.lane];
    const want = list.children[index - 1];
    if (moved || want !== node) list.insertBefore(node, want && want !== anchor ? want : anchor);
    if (moved && st.lastKey[s.run_id] !== undefined) {
      node.classList.remove('moved'); void node.offsetWidth; node.classList.add('moved');
    }
    st.lastKey[s.run_id] = key;
  }
  for (const [id, node] of st.strips) {
    if (!seen.has(id)) { node.remove(); st.strips.delete(id); delete st.lastKey[id]; }
  }
  for (const id of Object.keys(st.lists)) {
    const n = perLane[id] || 0;
    const limit = limitFor(id);
    st.counts[id].textContent = n ? String(n) : '';
    st.mores[id].textContent = n === 0 ? 'No runs' : n > limit ? `${n - limit} more` : '';
  }
  const empty = root.querySelector('.empty');
  empty.hidden = data.strips.length > 0 && data.session_open;
  empty.textContent = data.session_open
    ? 'No runs in this session yet. Send a webhook question to start one.'
    : 'No live session. Run make preflight to start one.';
  return () => { p.cleanups++; };
}
