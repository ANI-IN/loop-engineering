# Lantern Coffee Club business rules (the template's ground truth)

The rules every gold query in `dev.yaml` and `holdout.yaml` follows. The schema does not state
them; the starting knowledge version, `knowledge/v1.yaml`, states only the money rule. Replace
this file with your own warehouse's rules when you copy the template.

## Business rule 1: Money in cents

- Every money column holds whole cents. Report money in dollars, rounded to two decimals.

## Business rule 2: Refunds

- `payments.kind` codes: 1 charge, 2 refund, 3 test payment. The codes are not documented in the
  database.
- A refund is stored as a positive amount. Net revenue is the sum of charges minus the sum of
  refunds.
- Trap `refunds`: a query that sums every payment adds refunds instead of subtracting them.

## Business rule 3: Test payments

- Kind 3 rows are the team's own test payments. They never count: not in revenue, not in payment
  counts.
- Trap `test_payments`: a query that counts or sums every row includes them.

## Business rule 4: Pacific time

- Every day and month is read in Pacific time: `paid_ts AT TIME ZONE 'America/Los_Angeles'`
  before comparing with a date. The stored timestamps are UTC, so a payment early in the UTC day
  belongs to the previous Pacific day.
- Trap `pacific_time`: a query that compares `paid_ts` with a date directly counts the month in
  UTC.
