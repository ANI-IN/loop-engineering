"""Shared view furniture: the stamp, the projector styling, and the queue settings.

**Every view carries `computed HH:MM today · n=NN`.** A number on a projector with no
time and no n is indistinguishable from a number someone typed. Reference measurements
carry `measured <date>` instead, and are drawn differently — a stored figure must never
be able to pass for one computed in the room.
"""

import os
from datetime import datetime
from pathlib import Path

import gradio as gr

# Gradio defaults default_concurrency_limit to 1, which serialises every request. With
# two browsers open and a sweep running that reads as "the app hung". Bounded rather
# than unlimited: the model calls behind these views cost money, and an unbounded queue
# turns an impatient room clicking twice into double the spend.
CONCURRENCY_LIMIT = 4
MAX_QUEUE_SIZE = 24

NOT_MEASURED = "not yet measured"

# Large type, high contrast, few colours. Sized for the back of a room rather than for
# a laptop at arm's length; the projector is the only display that matters.
PROJECTOR_CSS = """
/* Sized for the back of a room first, a laptop second. One accent colour, used only
   where something is live; everything else earns attention through weight and space
   rather than hue, so the LIVE badge is the only saturated thing on the page. */
:root {
  --ink:      #0b1220;
  --body:     #1e293b;
  --muted:    #64748b;
  --hairline: #e2e8f0;
  --panel:    #ffffff;
  --canvas:   #f6f7f9;
  --live:     #0369a1;
  --live-bg:  #e0f2fe;
  --ref:      #92400e;
  --ref-bg:   #fef3c7;
  --warn:     #b91c1c;
  --ok:       #15803d;
}

.gradio-container {
  max-width: 1440px !important;
  background: var(--canvas) !important;
  padding: 8px 28px 48px !important;
}

/* ---- type scale -------------------------------------------------------- */
.gradio-container, .prose, .markdown-text, p, li, label, .gr-box {
  font-size: 19px !important;
  line-height: 1.62 !important;
  color: var(--body) !important;
  letter-spacing: -0.003em;
}
h1 {
  font-size: 44px !important; font-weight: 750 !important;
  color: var(--ink) !important; letter-spacing: -0.025em !important;
  margin: 18px 0 4px !important; line-height: 1.12 !important;
}
h2 {
  font-size: 29px !important; font-weight: 680 !important; color: var(--ink) !important;
  letter-spacing: -0.017em !important; margin: 34px 0 10px !important;
  padding-top: 22px; border-top: 1px solid var(--hairline);
}
h3 {
  font-size: 22px !important; font-weight: 640 !important; color: var(--ink) !important;
  letter-spacing: -0.011em !important; margin: 22px 0 8px !important;
}
strong, b { color: var(--ink) !important; font-weight: 650 !important; }
em { color: var(--muted) !important; }

/* ---- panels ------------------------------------------------------------ */
.gr-form, .gr-panel, .gr-box, .block {
  background: var(--panel) !important;
  border: 1px solid var(--hairline) !important;
  border-radius: 14px !important;
}
.gr-group { gap: 18px !important; }

/* ---- tables: the main way numbers reach the room ----------------------- */
table {
  font-size: 18px !important; border-collapse: separate !important;
  border-spacing: 0 !important; width: 100% !important;
  background: var(--panel); border-radius: 12px; overflow: hidden;
  border: 1px solid var(--hairline);
  font-variant-numeric: tabular-nums;
}
thead th {
  background: #f1f5f9 !important; color: var(--ink) !important;
  font-weight: 650 !important; font-size: 15.5px !important;
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 12px 16px !important; border-bottom: 1px solid var(--hairline) !important;
  text-align: left !important;
}
tbody td {
  padding: 13px 16px !important; border-bottom: 1px solid #f1f5f9 !important;
  vertical-align: top !important;
}
tbody tr:last-child td { border-bottom: none !important; }
tbody tr:hover td { background: #fafbfc !important; }

/* ---- code -------------------------------------------------------------- */
code, pre, pre code {
  font-size: 17px !important; line-height: 1.5 !important;
  font-family: ui-monospace, "SF Mono", Menlo, monospace !important;
}
:not(pre) > code {
  background: #f1f5f9 !important; color: var(--ink) !important;
  padding: 2px 7px !important; border-radius: 6px !important;
  font-size: 0.92em !important;
}
pre {
  background: #0f172a !important; border-radius: 12px !important;
  padding: 18px 20px !important; overflow-x: auto !important;
  border: none !important;
}
pre code { color: #e2e8f0 !important; }

/* ---- controls ---------------------------------------------------------- */
button {
  font-size: 19px !important; font-weight: 620 !important;
  padding: 13px 26px !important; border-radius: 11px !important;
  letter-spacing: -0.008em;
}
button.primary, .gr-button-primary {
  background: var(--live) !important; border-color: var(--live) !important;
}
button:disabled { opacity: 0.42 !important; cursor: not-allowed !important; }
input, textarea, select { font-size: 19px !important; border-radius: 10px !important; }

/* ---- the badges that carry the live/reference distinction -------------- */
.stamp {
  font-size: 16px !important; color: var(--muted) !important;
  letter-spacing: 0.012em; font-variant-numeric: tabular-nums;
}
.live-badge {
  color: var(--live) !important; background: var(--live-bg);
  font-weight: 700 !important; font-size: 14.5px !important;
  padding: 3px 10px; border-radius: 999px; white-space: nowrap;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.ref-badge {
  color: var(--ref) !important; background: var(--ref-bg);
  font-weight: 700 !important; font-size: 14.5px !important;
  padding: 3px 10px; border-radius: 999px; white-space: nowrap;
  text-transform: uppercase; letter-spacing: 0.05em;
}

/* ---- callouts ---------------------------------------------------------- */
blockquote {
  border-left: 4px solid var(--live) !important; background: #f8fafc !important;
  margin: 18px 0 !important; padding: 14px 20px !important;
  border-radius: 0 12px 12px 0 !important; color: var(--body) !important;
}

/* ---- tabs -------------------------------------------------------------- */
.tab-nav button {
  font-size: 19px !important; font-weight: 620 !important;
  padding: 12px 22px !important;
}

/* Wide content scrolls inside itself; the page never scrolls sideways. */
.overflow-x-auto, .table-wrap { overflow-x: auto !important; }
img { max-width: 100% !important; height: auto !important; }

@media (max-width: 820px) {
  .gradio-container { padding: 4px 14px 32px !important; }
  h1 { font-size: 32px !important; }
  h2 { font-size: 24px !important; }
  .gradio-container, p, li, table { font-size: 17px !important; }
}
"""


def stamp(n: int | None = None, *, computed_at: datetime | None = None) -> str:
    """`computed HH:MM today · n=NN`. The n is omitted only when there isn't one yet."""
    when = (computed_at or datetime.now()).strftime("%H:%M")
    tail = f" · n={n}" if n is not None else " · not yet measured"
    return f"<span class='stamp'>computed {when} today{tail}</span>"


def reference_stamp(measured_on: str, n: int | None = None) -> str:
    """Reference measurements never claim to have been computed now."""
    tail = f" · n={n}" if n is not None else ""
    return (
        f"<span class='stamp'><span class='ref-badge'>REFERENCE</span> · "
        f"measured {measured_on}{tail} · not computed in this session</span>"
    )


def live_or_reference_badge(is_reference: bool, measured_on: str = "") -> str:
    if is_reference:
        return f"<span class='ref-badge'>REFERENCE ({measured_on})</span>"
    return "<span class='live-badge'>LIVE</span>"


def lan_url(port: int | None) -> str | None:
    """The laptop's LAN address, so phones on the venue wifi can reach the app.

    A fallback for the share tunnel, not a replacement — many conference APs enable
    client isolation, which blocks device-to-device traffic and makes this fail exactly
    where it is most needed. Both paths get tested in the dry run.
    """
    import socket

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))  # no packet is sent; this just picks the route
        address = probe.getsockname()[0]
        probe.close()
        return f"http://{address}:{port or 7860}"
    except OSError:
        return None


def qr_png(url: str, path: Path | None = None) -> Path | None:
    """A QR for whichever URL is live. Nobody types a URL off a projector."""
    try:
        import qrcode
    except ImportError:
        return None
    target = Path(path or "results/share_qr.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    qrcode.make(url).save(target)
    return target


def launch(app: gr.Blocks, *, share: bool = False, port: int | None = None,
           prevent_thread_lock: bool = False, expose_lan: bool = True):
    """One place that knows the queue settings, so no view can forget them.

    Analytics are disabled here rather than per-view. Gradio phones home to
    huggingface.co and api.gradio.app on launch by default, which on a venue network
    is an outbound call that can hang a startup you are standing in front of — and it
    is not something a workshop needs to send anywhere.
    """
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    app.queue(default_concurrency_limit=CONCURRENCY_LIMIT, max_size=MAX_QUEUE_SIZE)
    # Launched non-blocking so the URLs below actually print. A blocking launch() means
    # everything after it runs at SHUTDOWN, which silently disabled the LAN address and
    # the QR code — the entire fallback for when a share tunnel cannot be reached.
    result = app.launch(
        share=share, server_port=port, prevent_thread_lock=True,
        # Gradio 6 moved css from the Blocks constructor to launch(). Without this the
        # projector styling is defined and never applied, which is the same class of
        # defect as a rule declared in config that nothing enforces.
        css=PROJECTOR_CSS,
        # 0.0.0.0 so the LAN URL actually resolves. Bound explicitly rather than left
        # to the default, which listens on loopback only and silently defeats the
        # fallback.
        server_name="0.0.0.0" if expose_lan else "127.0.0.1",
    )
    # Printed unbuffered and AFTER launch, because the share URL does not exist until
    # the tunnel is up. An earlier version of this looked like a share-link failure and
    # was only stdout block-buffering when redirected to a log.
    reachable = [u for u in (getattr(app, "share_url", None), lan_url(port)) if u]
    for url in reachable:
        print(f"  reachable at: {url}", flush=True)
    if reachable:
        made = qr_png(reachable[0])
        if made:
            print(f"  QR code: {made}", flush=True)

    if not prevent_thread_lock:
        # Hold the process open now that the URLs are out. The caller asked for a
        # blocking serve; it just needed to happen after the printing, not instead.
        try:
            app.block_thread()
        except (AttributeError, KeyboardInterrupt):
            pass
    return result
