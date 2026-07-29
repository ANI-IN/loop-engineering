"""The Level 3 event-driven loop: the question queue and its worker.

Runs the Level 2 loop from loopeng.verify against claimed rows. Deliberately
minimal — no backoff, no dead-lettering, no retries; a failed row goes to
status='failed' and stays there. Thin entry points in `demos/03_event_driven_loop/`.
"""
