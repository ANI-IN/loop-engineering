---
title: Loop Engineering
emoji: 🔁
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.20.0
python_version: "3.12"
app_file: app.py
pinned: false
hardware: cpu-basic
license: mit
short_description: Declared versus enforced rules in nested agent loops
---

# Loop Engineering — exhibit

A read-only exhibit from a workshop about the gap between a rule you declared and a rule
something actually enforces.

**This Space makes no model calls.** Every figure is a stored measurement, rendered with
the date it was taken. The live version runs from a laptop during the session, where the
same views compute their numbers in front of the room and stamp them with the time.

## What is live here, and what is not

**Fully live:** the verifier surface. Rule checking is a pure function over SQL text, so
every probe, every rule check and the AST-to-regex swap all run now, on stored queries,
at no cost. This is the most interesting part of the exhibit and it is not degraded.

**Frozen:** the sweep charts and the oversight panels. These are measurements, drawn as
hatched outlines and labelled with their date so a stored figure can never pass for one
computed just now.

**Disabled:** anything that would call a model. Those paths are disabled rather than
hidden, because a button that is merely invisible is still a button.

## What it is about

Four nested loops around a text-to-SQL agent: retrying on failure, verifying what the
retry cannot see, running with nobody watching, and measuring which configuration is
better. The argument is that a rule written in a config that nothing checks is not a
rule, and that a number without its n and its timestamp is not a measurement.

## Source

**<https://github.com/ANI-IN/loop-engineering-workshop>**

This Space is generated. It is pushed by `tools/sync_hf.py`, which stages the entry
point, the `loopeng` package and the committed reference measurements, and then
**refuses** to send `.env`, live sweep output, or any generated database — assertions
rather than filters, because a filter that misses is silent.

The four-loop framing is LangChain's [*The Art of Loop
Engineering*](https://www.langchain.com/blog/the-art-of-loop-engineering), which credits
swyx's [*Loopcraft: the art of stacking
loops*](https://www.latent.space/p/ainews-loopcraft-the-art-of-stacking). No assets are
reproduced from either; every diagram and chart here is generated from this project's own
control flow and measurements.
