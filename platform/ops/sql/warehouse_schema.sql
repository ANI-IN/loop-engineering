-- The warehouse schema of Harbor & Pine Outfitters, loaded by `make seed` as the owner role.
-- Tables are created without indexes; platform/ops/sql/warehouse_indexes.sql adds the keys and
-- indexes after the COPY. Comments describe columns only; business rules live in the knowledge
-- versions, never here.

DROP VIEW IF EXISTS warehouse.customers_marketable;
DROP TABLE IF EXISTS warehouse.order_items, warehouse.orders, warehouse.customers,
    warehouse.products, warehouse.categories CASCADE;

CREATE TABLE warehouse.categories (
    category_id  integer NOT NULL,
    name         text NOT NULL,
    parent_id    integer
);
COMMENT ON TABLE warehouse.categories IS 'Product categories.';
COMMENT ON COLUMN warehouse.categories.parent_id IS 'Parent category; empty for a top-level category.';

CREATE TABLE warehouse.products (
    product_id        integer NOT NULL,
    sku               text NOT NULL,
    name              text NOT NULL,
    category_id       integer NOT NULL,
    list_price_cents  integer NOT NULL,
    cost_cents        integer NOT NULL,
    is_active         boolean NOT NULL
);
COMMENT ON TABLE warehouse.products IS 'Products in the catalog.';
COMMENT ON COLUMN warehouse.products.category_id IS 'The category the product is listed in.';
COMMENT ON COLUMN warehouse.products.list_price_cents IS 'List price.';
COMMENT ON COLUMN warehouse.products.cost_cents IS 'Unit cost.';
COMMENT ON COLUMN warehouse.products.is_active IS 'Whether the product is currently sold.';

CREATE TABLE warehouse.customers (
    customer_id   integer NOT NULL,
    first_name    text NOT NULL,
    last_name     text NOT NULL,
    email         text NOT NULL,
    phone         text,
    city          text NOT NULL,
    state         char(2) NOT NULL,
    zip           text NOT NULL,
    created_at    timestamptz NOT NULL,
    ccpa_opt_out  boolean NOT NULL
);
COMMENT ON TABLE warehouse.customers IS 'Customer accounts.';
COMMENT ON COLUMN warehouse.customers.email IS 'Email address.';
COMMENT ON COLUMN warehouse.customers.phone IS 'Phone number, when given.';
COMMENT ON COLUMN warehouse.customers.state IS 'State of the account address.';
COMMENT ON COLUMN warehouse.customers.zip IS 'Zip code of the account address.';
COMMENT ON COLUMN warehouse.customers.created_at IS 'When the account was created.';
COMMENT ON COLUMN warehouse.customers.ccpa_opt_out IS 'Opted out of the sale or sharing of personal data.';

CREATE TABLE warehouse.orders (
    order_id        integer NOT NULL,
    customer_id     integer NOT NULL,
    order_ts        timestamptz NOT NULL,
    status          smallint NOT NULL,
    channel         text NOT NULL,
    ship_state      char(2) NOT NULL,
    subtotal_cents  integer NOT NULL,
    discount_cents  integer NOT NULL,
    tax_amount      integer NOT NULL,
    shipping_cents  integer NOT NULL,
    total_cents     integer NOT NULL
);
COMMENT ON TABLE warehouse.orders IS 'Customer orders.';
COMMENT ON COLUMN warehouse.orders.order_ts IS 'When the order was placed.';
COMMENT ON COLUMN warehouse.orders.status IS 'Order status code.';
COMMENT ON COLUMN warehouse.orders.channel IS 'Where the order was placed: web or app.';
COMMENT ON COLUMN warehouse.orders.ship_state IS 'State the order ships to.';
COMMENT ON COLUMN warehouse.orders.subtotal_cents IS 'Sum of the order lines.';
COMMENT ON COLUMN warehouse.orders.discount_cents IS 'Discount applied to the order.';
COMMENT ON COLUMN warehouse.orders.tax_amount IS 'Tax charged on the order.';
COMMENT ON COLUMN warehouse.orders.shipping_cents IS 'Shipping charged on the order.';
COMMENT ON COLUMN warehouse.orders.total_cents IS 'Amount charged for the order.';

CREATE TABLE warehouse.order_items (
    order_item_id     integer NOT NULL,
    order_id          integer NOT NULL,
    product_id        integer NOT NULL,
    quantity          integer NOT NULL,
    unit_price_cents  integer NOT NULL
);
COMMENT ON TABLE warehouse.order_items IS 'Order lines.';
COMMENT ON COLUMN warehouse.order_items.unit_price_cents IS 'Price of one unit on this order.';
