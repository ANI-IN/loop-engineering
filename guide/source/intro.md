# Module: Loop Engineering - Introduction: why this guide exists

An analytics agent at work answers a finance question with a confident number that is wrong. It
passes every check on its query, posts the same answer three times when a webhook retries, and
loses an approval when its worker restarts. Rules written from its failures raise its score on the
questions they quote and break others. More prompting fixes none of this: each failure is a missing
loop around the model.

This guide walks through every live demo of the class, one command and one screen at a time. The
demos run on DataPilot, an analytics agent over the Harbor & Pine Outfitters warehouse, watched on
its console. Each answer is scored against a gold query on two databases, and the question that
matters, "What was our net revenue in fiscal year 2025?", is fixed before any run.

There is one chapter per section, one loop per chapter. The results are measured, not promised:
the starting knowledge fails every trap, the graders pass a wrong answer, and the promoted
knowledge answers the spine question correctly without earning the unattended level for revenue
in any measured run. Each chapter shows what its run found and what to say about it in class.
