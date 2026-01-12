VALID_QUERIES = [
    "SELECT o.id, o.total_amount, o.status FROM orders o WHERE o.status = 'completed' LIMIT 100",
    "SELECT c.country, COUNT(o.id) AS order_count FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.country ORDER BY order_count DESC LIMIT 20",
    "SELECT DATE_TRUNC('month', created_at) AS month, SUM(total_amount) AS revenue FROM orders GROUP BY month ORDER BY month",
]

INVALID_QUERIES_SAFETY = [
    "DROP TABLE orders",
    "DELETE FROM customers WHERE id = '123'",
    "UPDATE orders SET status = 'deleted' WHERE 1=1",
    "ALTER TABLE orders ADD COLUMN foo TEXT",
]

INVALID_QUERIES_SYNTAX = [
    "SELCT * FROM orders",
    "SELECT FROM",
    "SELECT id FROM WHERE status = 'ok'",
]

INVALID_QUERIES_SCHEMA = [
    "SELECT ghost_column FROM orders LIMIT 10",
    "SELECT id FROM nonexistent_table LIMIT 10",
    "SELECT o.fake_col FROM orders o LIMIT 10",
]
