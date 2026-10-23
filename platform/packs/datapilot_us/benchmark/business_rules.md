# Harbor & Pine business rules (instructor ground truth)

This page is the ground truth the gold SQL follows. It is never given to the agent: the agent
learns these rules only through knowledge versions that pass the promotion gate. Nothing in the
warehouse schema, its comments, or its sample data states them.

## Business rule 1: Fiscal year

- The fiscal year runs from February 1 to January 31 and is named by the calendar year it ends in.
  Fiscal year 2025 is February 1, 2024 to January 31, 2025.
- Fiscal quarters: first quarter February to April, second May to July, third August to October,
  fourth November to January.
- Fiscal periods are counted in Eastern time (business rule 5).
- The warehouse holds fiscal years 2024, 2025, and 2026 (February 1, 2023 to January 31, 2026).

## Business rule 2: Money in cents

- Every money column holds whole cents, including `tax_amount`. Report money in dollars,
  rounded to two decimals.

## Business rule 3: Net revenue

- Revenue, sales, and net revenue all mean `subtotal_cents - discount_cents`.
- Tax (`tax_amount`) and shipping (`shipping_cents`) are not revenue. `total_cents` is what the
  customer was charged and is never used for revenue.
- Average order value is net revenue divided by the number of counted orders.

## Business rule 4: Cancelled orders

- `orders.status` codes: 1 placed, 2 paid, 3 shipped, 4 delivered, 5 cancelled. The codes are not
  documented anywhere in the warehouse.
- Cancelled orders (status 5) are excluded from revenue, order counts, averages, units sold, and
  customer counts based on orders, such as a customer's first order.

## Business rule 5: Eastern business days

- Every date, day, week, month, and hour is read in Eastern time:
  `order_ts AT TIME ZONE 'America/New_York'` before truncating or comparing with a date. The
  stored timestamps are UTC, so an evening Eastern time order falls on the next UTC date.
- Business days are Monday to Friday, except the company holidays: Memorial Day, Independence
  Day, Labor Day, Thanksgiving Day, Christmas Day, and New Year's Day. In the warehouse range:
  2023-05-29, 2023-07-04, 2023-09-04, 2023-11-23, 2023-12-25, 2024-01-01, 2024-05-27, 2024-07-04,
  2024-09-02, 2024-11-28, 2024-12-25, 2025-01-01, 2025-05-26, 2025-07-04, 2025-09-01, 2025-11-27,
  2025-12-25, 2026-01-01.
- Black Friday is the day after Thanksgiving; Cyber Monday is the Monday after it.

## Business rule 6: Internal accounts

- Customers whose email domain is `harborpine.com` are staff and test accounts. The domain is
  stored in mixed case, so compare `lower(email) LIKE '%@harborpine.com'`. A few real customers
  have "harborpine" in the part before the `@`; they are not internal.
- Internal accounts and their orders are excluded from every metric and every customer list.
- Their test orders add about 2.5 percent to revenue (2.8 percent in warehouse_alt). Three heavy
  internal accounts rank among the top 10 customers by revenue in every fiscal year; the other
  internal accounts stay far below the top 10.

## Business date

- "Today" is the business date, 31 January 2026 (a Saturday, the last day of fiscal year 2026),
  set by DATAPILOT_BUSINESS_DATE. Relative dates resolve against it: yesterday is 30 January 2026,
  last month is December 2025, this quarter is the fourth quarter of fiscal year 2026 (November
  2025 to January 2026), this fiscal year is fiscal year 2026, and last fiscal year is fiscal year
  2025. Gold SQL always uses literal dates, never CURRENT_DATE or now().

## Marketing audience

- `warehouse.customers_marketable` is the marketing audience: it leaves out customers who opted
  out (`ccpa_opt_out`) and internal accounts. Questions about the marketing audience use the
  view.

## Data conditions kept on purpose

- About 6 percent of orders are cancelled (7.5 percent in warehouse_alt).
- 10 to 15 percent of orders cross the UTC date boundary, including on the days around both
  daylight saving changes.
- Three product names carry prompt-injection text, and two product names are nearly identical
  ("Alpine Trek 45L Backpack" and "Alpine Trek 45 L Backpack").
- Tax rates are illustrative and fictional; they are zero in Alaska, Delaware, Montana, New
  Hampshire, and Oregon.
- warehouse_alt has the same schema and catalog with a different seed, fewer customers, other
  prices, rates, and shares, so an answer that matches gold on both databases computes the right
  thing rather than recalling a number.
