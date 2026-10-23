# [Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) <!-- check-style: allow SC33 the source title is quoted as published -->

Reading time: about 20 minutes.
Source: Malcolm Featonby (Amazon Web Services), [Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/), n.d.

> **Terms on this page**
>
> - **Idempotency**: Running the same event twice has the effect of running it once.
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.

## Why it matters

The duplicate events demo sends the same event three times and posts one answer. This article from
the Amazon Builders' Library explains why that property is not optional once work runs from
events and retries: a retry is the simplest way to recover from a failure, and without idempotency
every retry risks a second effect. The article is about cloud resources; the same holds for a
revenue digest posted twice.

## Three key ideas

1. **Retries have side effects.** The article's example: it "would be undesirable for the EC2
   instance launch workflow to retry a failed call to create an EBS volume and end up with two EBS
   volumes." The answer is idempotency: "An idempotent operation is one where a request can be
   retransmitted or retried with no additional side effects."

2. **The caller states its intent with a key.** "A unique caller-provided client request
   identifier for idempotent operations meets this need." On a request, the service "first checks
   to see if it has seen this identifier before." DataPilot's `POST /events` does the same with
   `ON CONFLICT (event_id) DO NOTHING`, and the scheduler derives the digest's key from the day,
   `digest:YYYY-MM-DD`. A random key, the random digest id (`BUG_RANDOM_DIGEST_ID`), defeats it.

3. **Record the key and the effect together.** "The process that combines recording the idempotent
   token and all mutating operations related to servicing the request must meet the properties for
   an atomic, consistent, isolated, and durable (ACID) operation." DataPilot writes the event row
   and the job row in one transaction for this reason, so a crash never leaves a key without its
   job.

## Apply it to your repository

1. List every effect your agent has outside its own state: a post, an email, a ticket, an export.
2. For each one, name the key that makes a repeat harmless. If you cannot, the effect is not safe
   to retry.
3. Derive keys from what the event means, such as the day of a digest, rather than from a random
   value, and store the key in the same transaction as the effect.
4. Send one event twice on purpose, as `make demo NAME=events-duplicate-events` does, and count
   the effects.

## Sources

- Source 1: Making retries safe with idempotent APIs, <https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/>, Malcolm Featonby (Amazon Web Services), n.d.
