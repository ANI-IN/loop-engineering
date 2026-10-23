-- Keys, indexes, and the marketing view, applied by `make seed` after the COPY (owner role).

ALTER TABLE warehouse.categories ADD PRIMARY KEY (category_id);
ALTER TABLE warehouse.categories
    ADD FOREIGN KEY (parent_id) REFERENCES warehouse.categories (category_id);

ALTER TABLE warehouse.products ADD PRIMARY KEY (product_id);
ALTER TABLE warehouse.products ADD UNIQUE (sku);
ALTER TABLE warehouse.products
    ADD FOREIGN KEY (category_id) REFERENCES warehouse.categories (category_id);

ALTER TABLE warehouse.customers ADD PRIMARY KEY (customer_id);

ALTER TABLE warehouse.orders ADD PRIMARY KEY (order_id);
ALTER TABLE warehouse.orders
    ADD FOREIGN KEY (customer_id) REFERENCES warehouse.customers (customer_id);
CREATE INDEX orders_by_time ON warehouse.orders (order_ts);
CREATE INDEX orders_by_customer ON warehouse.orders (customer_id);

ALTER TABLE warehouse.order_items ADD PRIMARY KEY (order_item_id);
ALTER TABLE warehouse.order_items
    ADD FOREIGN KEY (order_id) REFERENCES warehouse.orders (order_id);
ALTER TABLE warehouse.order_items
    ADD FOREIGN KEY (product_id) REFERENCES warehouse.products (product_id);
CREATE INDEX order_items_by_order ON warehouse.order_items (order_id);
CREATE INDEX order_items_by_product ON warehouse.order_items (product_id);

CREATE VIEW warehouse.customers_marketable AS
SELECT customer_id, first_name, last_name, email, phone, city, state, zip, created_at
FROM warehouse.customers
WHERE NOT ccpa_opt_out
  AND lower(email) NOT LIKE '%@harborpine.com';
COMMENT ON VIEW warehouse.customers_marketable IS 'Customers who may receive marketing.';
