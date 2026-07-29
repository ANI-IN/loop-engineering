"""The Level 1 agent loop: ask, run SQL, retry on failure.

Implementation lives here, not in demos/. `demos/01_agent_loop/` holds thin entry
points that wire arguments, call in here, and render — nothing more. The four loops
are nested rather than parallel (L2 wraps L1, L3 runs L2, L4 sweeps both), so a
second copy of the loop in a demo file is a second place for it to drift, and every
number the room sees has to come from one system.
"""
