function probe(name) {
  const all = (window.__dpProbe = window.__dpProbe || {});
  return (all[name] = all[name] || { calls: 0, mounts: 0, cleanups: 0 });
}
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = String(text);
  return n;
}
function flash(node) {
  node.classList.remove('changed'); void node.offsetWidth; node.classList.add('changed');
}
function rid() { return Math.random().toString(36).slice(2, 10); }
function link(href, text) {
  const a = el('a', 'trace', text);
  a.href = href; a.target = '_blank'; a.rel = 'noopener';
  return a;
}
// Times arrive as UTC ISO strings and are formatted here, in the viewer's time zone, or in the
// zone the server passes as display_tz (DATAPILOT_DISPLAY_TIMEZONE). The server never formats them.
function fmtTime(iso, tz, seconds = true) {
  const opts = { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' };
  if (seconds) opts.second = '2-digit';
  if (tz) opts.timeZone = tz;
  try {
    return new Intl.DateTimeFormat('en-GB', opts).format(new Date(iso));
  } catch (error) {
    delete opts.timeZone;
    return new Intl.DateTimeFormat('en-GB', opts).format(new Date(iso));
  }
}
// The live stamp, on one line: "Started 11:59:09. Open trace".
function stampLine(stamp, tz, linkText) {
  const line = el('div', 'stamp', `Started ${fmtTime(stamp.started_at_utc, tz)}`);
  if (stamp.trace_url) {
    line.append(document.createTextNode('. '), link(stamp.trace_url, linkText || 'Open trace'));
  }
  return line;
}
const fmt = new Intl.NumberFormat('en-US');
