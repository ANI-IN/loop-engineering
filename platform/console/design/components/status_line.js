export default function (component) {
  const { parentElement: root, data } = component;
  const p = probe('status_line');
  p.calls++;
  let s = root.__dp;
  if (!s) {
    s = root.__dp = { instance: rid(), armed: false, timer: null, left: 0, prev: {} };
    p.mounts++;
    root.querySelector('.sl').dataset.instance = s.instance;
    const kill = root.querySelector('.kill');
    const disarm = () => {
      s.armed = false; clearInterval(s.timer); s.timer = null; paintKill();
    };
    s.disarm = disarm;
    kill.addEventListener('click', () => {
      if (s.data.kill === 'engaged') { s.trigger('release', Date.now()); return; }
      if (!s.armed) {
        // The disarm time comes from pack.yaml (console.kill_switch_disarm_seconds).
        s.armed = true; s.left = s.data.disarm_seconds;
        s.timer = setInterval(() => {
          s.left -= 1;
          if (s.left <= 0) disarm(); else paintKill();
        }, 1000);
        paintKill();
      } else {
        disarm();
        s.trigger('stop_all', Date.now());
      }
    });
    kill.addEventListener('keydown', (e) => { if (e.key === 'Escape' && s.armed) disarm(); });
    function paintKill() {
      const msg = root.querySelector('.msg');
      kill.classList.toggle('armed', s.armed);
      kill.classList.toggle('engaged', s.data.kill === 'engaged');
      if (s.data.kill === 'engaged') {
        kill.textContent = 'Release kill switch';
        msg.textContent =
          'Kill switch engaged. All workers stopped; autonomy forced to the report-only level.';
      } else if (s.armed) {
        kill.textContent = 'Click again to stop all workers';
        msg.textContent =
          'Armed. A second click stops every worker and forces the report-only level. ' +
          `Disarms in ${s.left} s, or press Escape.`;
      } else {
        kill.textContent = 'Kill switch';
        msg.textContent = '';
      }
    }
    s.paintKill = paintKill;
  }
  s.data = data;
  s.trigger = component.setTriggerValue;
  const prev = s.prev;
  const f = (name) => root.querySelector(`[data-f="${name}"]`);

  const session = f('session');
  session.textContent = data.session
    ? `Session started ${fmtTime(data.session.started_at_utc, data.display_tz, false)}`
    : 'No live session. Run make preflight to start one.';
  session.classList.toggle('nosession', !data.session);
  f('business').textContent = data.business_date;
  f('tz').textContent = data.display_tz
    ? `Times are in ${data.display_tz}`
    : 'Times are in your local time';

  const autonomy = data.autonomy + (data.forced ? ', forced by the kill switch' : '');
  if (prev.autonomy !== autonomy) {
    f('autonomy').textContent = autonomy;
    if (prev.autonomy !== undefined) flash(f('autonomy'));
  }

  const famKey = JSON.stringify([data.families, data.forced]);
  if (prev.fam !== famKey) {
    const box = f('families'); box.replaceChildren();
    // Cleared families one by one; the kill switch suspends them (hollow mark, word says so).
    for (const fam of data.families.filter((x) => x.cleared)) {
      const live = !data.forced;
      const item = el('span', 'f' + (live ? ' cleared' : ''));
      item.append(el('span', 'mark ' + (live ? 'filled' : 'hollow')),
                  el('span', '', live ? fam.name : `${fam.name}: suspended`));
      box.append(item);
    }
    const rest = data.families.filter((x) => !x.cleared).map((x) => x.name);
    if (rest.length) {
      const item = el('span', 'f');
      item.append(el('span', 'mark hollow'), el('span', '', `Not cleared: ${rest.join(', ')}`));
      box.append(item);
    }
    if (prev.fam !== undefined) flash(box);
  }

  const gauge = root.querySelector('.gauge');
  gauge.classList.toggle('near', data.gauge === 'near');
  gauge.classList.toggle('cap', data.gauge === 'cap');
  root.querySelector('.fill').style.width = `${Math.round(data.share * 100)}%`;
  f('tokens').textContent = `${fmt.format(data.tokens_used)} of ${fmt.format(data.tokens_cap)}`;
  f('gauge').textContent =
    { ok: '', near: 'Near the daily cap', cap: 'Cap reached: new runs blocked' }[data.gauge];

  const chipKey = JSON.stringify([data.planted, data.pacing]);
  if (prev.chips !== chipKey) {
    const box = f('chips'); box.replaceChildren();
    box.append(el('span', 'k', 'Planted'));
    if (!data.planted.length) box.append(el('span', 'none', 'None: the fixed system'));
    for (const name of data.planted) box.append(el('span', 'chip', name));
    if (data.pacing) {
      box.append(el('span', 'chip aid', `Demo pacing on: ${data.pacing} s between stages`));
    }
  }

  const engagedChanged = prev.kill !== undefined && prev.kill !== data.kill;
  if (engagedChanged && s.armed) s.disarm();
  root.querySelector('.sl').classList.toggle('engaged', data.kill === 'engaged');
  s.paintKill();
  if (engagedChanged) flash(root.querySelector('.msg'));

  s.prev = { autonomy, fam: famKey, chips: chipKey, kill: data.kill };
  return () => { p.cleanups++; };
}
