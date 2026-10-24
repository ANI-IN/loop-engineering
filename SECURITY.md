# Security policy

## Report a problem privately

If you find a security problem in this repository, such as a way for the agent to write to the
warehouse, read data its role should not see, or leak an application programming interface (API)
key, report it privately.

The private channel is GitHub's private vulnerability reporting, once the maintainers have turned
it on for this repository:

1. Open the repository's **Security** tab on GitHub.
2. If it offers **Report a vulnerability**, choose it and fill in the form. This opens a private
   security advisory that only the maintainers can see.

If the **Security** tab does not offer **Report a vulnerability** yet, open a public issue titled
"Security contact request" and write nothing else in it: no details of the problem, no steps, no
logs. A maintainer answers on the issue with a private way to send the report.

Please do not describe the problem in a public issue or post about it in a course channel until it
is fixed.

## Never post a key

Never paste an API key, your `.env` file, or a screenshot that shows either into an advisory, an
issue, a pull request, a support ticket, or a chat. Describe the problem and the steps to repeat it
instead. If a key was exposed anywhere, delete it on the provider's page (OpenAI or LangSmith) and
create a new one.

## What is in scope

- The DataPilot platform in `platform/`: the agent, the graders and executor, the API service,
  the worker, the scheduler, and the console.
- The database roles and the read-only startup probe in `platform/ops/`.
- The course scripts and the continuous integration workflow.

DataPilot ships planted bugs on purpose, each off by default and listed in
`docs/planted-items.md`, such as the naive guard (`BUG_NAIVE_GUARD`). Those are part of the
lessons, not security reports.
