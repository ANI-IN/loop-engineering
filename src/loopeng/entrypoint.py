"""One place where a missing credential becomes the sentence it already wrote.

`settings.py` opens by promising that "every failure names the exact environment
variable and the exact fix". It builds exactly that sentence. Then eight of the
nine entry points let `MissingCredential` propagate out of `main()`, and Python
printed a twenty-five line pydantic traceback whose last line happened to contain
it — so the promise was kept by the module that made it and broken by everything
that called it.

`preflight.py` was the one place that caught it, which is why the preflight is the
only demo whose keyless failure reads like it was designed.

Thin on purpose: this is the same "thin by rule" boundary the demos already keep.
It converts an exception to an exit code and a message, and does nothing else.
"""

import sys
from collections.abc import Callable

from loopeng.settings import MissingCredential


def run(main: Callable[[], int]) -> int:
    """Call an entry point's `main`, rendering a missing credential as its message.

    Returns 1 rather than raising, so the shell sees a failure and the operator
    sees the fix. Any other exception is left alone: a traceback is the right
    output for a defect, and wrong for a configuration problem the user can act
    on in one command.
    """
    try:
        return main()
    except MissingCredential as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return 1
