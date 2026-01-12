-- Demo e-commerce dataset (customers, products, orders, order_items) in the
-- `demo` database, queried via the read-only querymind_reader role.
\connect demo

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'querymind_reader') THEN
        CREATE ROLE querymind_reader WITH LOGIN PASSWORD 'querymind_reader';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE demo TO querymind_reader;
GRANT USAGE ON SCHEMA public TO querymind_reader;

-- ── Tables ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    email       VARCHAR(200) NOT NULL UNIQUE,
    country     VARCHAR(100),
    segment     VARCHAR(50) CHECK (segment IN ('enterprise', 'smb', 'consumer')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(300) NOT NULL,
    category    VARCHAR(100),
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    sku         VARCHAR(100) UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID NOT NULL REFERENCES customers (id),
    total_amount    NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    status          VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'cancelled', 'refunded')),
    region          VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS order_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id    UUID NOT NULL REFERENCES orders (id),
    product_id  UUID NOT NULL REFERENCES products (id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10, 2) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_orders_customer_id   ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status        ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at    ON orders (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_customers_country    ON customers (country);
CREATE INDEX IF NOT EXISTS idx_customers_segment    ON customers (segment);
CREATE INDEX IF NOT EXISTS idx_products_category    ON products (category);

-- ── Grants ────────────────────────────────────────────────────────────────────

GRANT SELECT ON ALL TABLES IN SCHEMA public TO querymind_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO querymind_reader;

-- ── Customers (20 rows, 10 countries, 3 segments) ─────────────────────────────

INSERT INTO customers (name, email, country, segment) VALUES
    ('Acme Corporation',      'acme@example.com',       'US', 'enterprise'),
    ('Beta Systems Ltd',      'beta@example.com',       'UK', 'enterprise'),
    ('Gamma Tech GmbH',       'gamma@example.com',      'DE', 'enterprise'),
    ('Delta Digital SA',      'delta@example.com',      'FR', 'smb'),
    ('Epsilon Media Inc',     'epsilon@example.com',    'US', 'consumer'),
    ('Zeta Software Oy',      'zeta@example.com',       'FI', 'smb'),
    ('Eta Solutions Srl',     'eta@example.com',        'IT', 'smb'),
    ('Theta Cloud Pte',       'theta@example.com',      'SG', 'enterprise'),
    ('Iota Labs Inc',         'iota@example.com',       'CA', 'smb'),
    ('Kappa Systems KK',      'kappa@example.com',      'JP', 'enterprise'),
    ('Lambda Corp LLC',       'lambda@example.com',     'US', 'enterprise'),
    ('Mu Analytics Pty',      'mu@example.com',         'AU', 'smb'),
    ('Nu Digital Ltda',       'nu@example.com',         'BR', 'consumer'),
    ('Xi Technologies',       'xi@example.com',         'IN', 'smb'),
    ('Omicron AI Inc',        'omicron@example.com',    'US', 'enterprise'),
    ('Pi Networks GmbH',      'pi@example.com',         'DE', 'smb'),
    ('Rho Consulting SA',     'rho@example.com',        'FR', 'enterprise'),
    ('Sigma Data AB',         'sigma@example.com',      'SE', 'consumer'),
    ('Tau Networks BV',       'tau@example.com',        'NL', 'smb'),
    ('Upsilon Data Inc',      'upsilon@example.com',    'US', 'consumer')
ON CONFLICT DO NOTHING;

-- ── Products (15 rows, 5 categories) ─────────────────────────────────────────

INSERT INTO products (name, category, price, sku) VALUES
    -- Hardware
    ('DataNode Server',            'Hardware',  1999.99, 'HW-001'),
    ('Network Switch Pro',         'Hardware',   399.99, 'HW-002'),
    ('Edge Device Kit',            'Hardware',   149.99, 'HW-003'),
    -- Software
    ('Analytics Platform',         'Software',   299.99, 'SW-001'),
    ('Data Pipeline Pro',          'Software',   199.99, 'SW-002'),
    ('ML Workbench',               'Software',   499.99, 'SW-003'),
    ('Query Builder Enterprise',   'Software',    99.99, 'SW-004'),
    -- Services
    ('Onboarding Package',         'Services',   999.99, 'SV-001'),
    ('Enterprise Support',         'Services',  1499.99, 'SV-002'),
    ('Migration Service',          'Services',  2999.99, 'SV-003'),
    -- Analytics
    ('Business Intelligence Suite','Analytics',  349.99, 'AN-001'),
    ('Reporting Bundle',           'Analytics',  149.99, 'AN-002'),
    -- Security
    ('Security Audit',             'Security',   799.99, 'SC-001'),
    ('Compliance Pack',            'Security',  1299.99, 'SC-002'),
    ('Penetration Test',           'Security',  2499.99, 'SC-003')
ON CONFLICT DO NOTHING;

-- ── Orders + Items ────────────────────────────────────────────────────────────
-- Order IDs use the pattern 00000000-0000-4000-a000-{N} for easy item cross-ref.
-- total_amount = sum of (unit_price * quantity) for that order's items.

DO $$
DECLARE
    -- Customer IDs
    c_acme    UUID := (SELECT id FROM customers WHERE email = 'acme@example.com');
    c_beta    UUID := (SELECT id FROM customers WHERE email = 'beta@example.com');
    c_gamma   UUID := (SELECT id FROM customers WHERE email = 'gamma@example.com');
    c_delta   UUID := (SELECT id FROM customers WHERE email = 'delta@example.com');
    c_eps     UUID := (SELECT id FROM customers WHERE email = 'epsilon@example.com');
    c_zeta    UUID := (SELECT id FROM customers WHERE email = 'zeta@example.com');
    c_eta     UUID := (SELECT id FROM customers WHERE email = 'eta@example.com');
    c_theta   UUID := (SELECT id FROM customers WHERE email = 'theta@example.com');
    c_iota    UUID := (SELECT id FROM customers WHERE email = 'iota@example.com');
    c_kappa   UUID := (SELECT id FROM customers WHERE email = 'kappa@example.com');
    c_lambda  UUID := (SELECT id FROM customers WHERE email = 'lambda@example.com');
    c_mu      UUID := (SELECT id FROM customers WHERE email = 'mu@example.com');
    c_nu      UUID := (SELECT id FROM customers WHERE email = 'nu@example.com');
    c_xi      UUID := (SELECT id FROM customers WHERE email = 'xi@example.com');
    c_omicron UUID := (SELECT id FROM customers WHERE email = 'omicron@example.com');
    c_pi      UUID := (SELECT id FROM customers WHERE email = 'pi@example.com');
    c_rho     UUID := (SELECT id FROM customers WHERE email = 'rho@example.com');
    c_sigma   UUID := (SELECT id FROM customers WHERE email = 'sigma@example.com');
    c_tau     UUID := (SELECT id FROM customers WHERE email = 'tau@example.com');
    c_upsilon UUID := (SELECT id FROM customers WHERE email = 'upsilon@example.com');

    -- Product IDs
    p_hw1 UUID := (SELECT id FROM products WHERE sku = 'HW-001');
    p_hw2 UUID := (SELECT id FROM products WHERE sku = 'HW-002');
    p_hw3 UUID := (SELECT id FROM products WHERE sku = 'HW-003');
    p_sw1 UUID := (SELECT id FROM products WHERE sku = 'SW-001');
    p_sw2 UUID := (SELECT id FROM products WHERE sku = 'SW-002');
    p_sw3 UUID := (SELECT id FROM products WHERE sku = 'SW-003');
    p_sw4 UUID := (SELECT id FROM products WHERE sku = 'SW-004');
    p_sv1 UUID := (SELECT id FROM products WHERE sku = 'SV-001');
    p_sv2 UUID := (SELECT id FROM products WHERE sku = 'SV-002');
    p_sv3 UUID := (SELECT id FROM products WHERE sku = 'SV-003');
    p_an1 UUID := (SELECT id FROM products WHERE sku = 'AN-001');
    p_an2 UUID := (SELECT id FROM products WHERE sku = 'AN-002');
    p_sc1 UUID := (SELECT id FROM products WHERE sku = 'SC-001');
    p_sc2 UUID := (SELECT id FROM products WHERE sku = 'SC-002');
    p_sc3 UUID := (SELECT id FROM products WHERE sku = 'SC-003');
BEGIN

-- ── Orders ────────────────────────────────────────────────────────────────────
INSERT INTO orders (id, customer_id, total_amount, status, region, created_at, completed_at) VALUES
-- Q4 2024
('00000000-0000-4000-a000-000000000001', c_acme,    4299.97, 'completed', 'North America', '2024-10-08 09:00:00+00', '2024-10-10 15:00:00+00'),
('00000000-0000-4000-a000-000000000002', c_beta,    1499.99, 'completed', 'Europe',        '2024-11-05 10:30:00+00', '2024-11-07 11:00:00+00'),
('00000000-0000-4000-a000-000000000003', c_gamma,   1299.99, 'completed', 'Europe',        '2024-11-18 08:00:00+00', '2024-11-20 14:00:00+00'),
('00000000-0000-4000-a000-000000000004', c_theta,   1199.97, 'completed', 'Asia Pacific',  '2024-12-03 06:00:00+00', '2024-12-05 08:00:00+00'),
('00000000-0000-4000-a000-000000000005', c_kappa,    749.96, 'completed', 'Asia Pacific',  '2024-12-14 07:00:00+00', '2024-12-16 09:00:00+00'),

-- January 2025
('00000000-0000-4000-a000-000000000006', c_acme,    2099.97, 'completed', 'North America', '2025-01-05 09:00:00+00', '2025-01-07 14:00:00+00'),
('00000000-0000-4000-a000-000000000007', c_beta,    1999.99, 'completed', 'Europe',        '2025-01-10 11:00:00+00', '2025-01-12 09:00:00+00'),
('00000000-0000-4000-a000-000000000008', c_gamma,    999.98, 'completed', 'Europe',        '2025-01-15 08:00:00+00', '2025-01-17 10:00:00+00'),
('00000000-0000-4000-a000-000000000009', c_theta,   2099.98, 'completed', 'Asia Pacific',  '2025-01-20 06:00:00+00', '2025-01-22 07:00:00+00'),
('00000000-0000-4000-a000-000000000010', c_kappa,    499.95, 'cancelled', 'Asia Pacific',  '2025-01-25 07:00:00+00', NULL),

-- February 2025
('00000000-0000-4000-a000-000000000011', c_acme,    3999.98, 'completed', 'North America', '2025-02-03 09:00:00+00', '2025-02-05 16:00:00+00'),
('00000000-0000-4000-a000-000000000012', c_omicron,  899.97, 'completed', 'North America', '2025-02-08 10:00:00+00', '2025-02-10 13:00:00+00'),
('00000000-0000-4000-a000-000000000013', c_rho,     2999.98, 'completed', 'Europe',        '2025-02-12 09:00:00+00', '2025-02-14 11:00:00+00'),
('00000000-0000-4000-a000-000000000014', c_gamma,    849.96, 'processing','Europe',        '2025-02-20 08:00:00+00', NULL),
('00000000-0000-4000-a000-000000000015', c_xi,       749.97, 'completed', 'Asia Pacific',  '2025-02-25 05:00:00+00', '2025-02-27 08:00:00+00'),

-- March 2025
('00000000-0000-4000-a000-000000000016', c_lambda,  2299.98, 'completed', 'North America', '2025-03-04 09:00:00+00', '2025-03-06 14:00:00+00'),
('00000000-0000-4000-a000-000000000017', c_eta,      449.97, 'completed', 'Europe',        '2025-03-07 08:00:00+00', '2025-03-09 10:00:00+00'),
('00000000-0000-4000-a000-000000000018', c_xi,       599.97, 'completed', 'Asia Pacific',  '2025-03-11 06:00:00+00', '2025-03-13 09:00:00+00'),
('00000000-0000-4000-a000-000000000019', c_mu,       699.98, 'completed', 'Asia Pacific',  '2025-03-18 04:00:00+00', '2025-03-20 06:00:00+00'),
('00000000-0000-4000-a000-000000000020', c_zeta,     499.97, 'refunded',  'Europe',        '2025-03-22 10:00:00+00', NULL),
('00000000-0000-4000-a000-000000000021', c_iota,     349.99, 'completed', 'North America', '2025-03-28 14:00:00+00', '2025-03-30 16:00:00+00'),

-- April 2025
('00000000-0000-4000-a000-000000000022', c_acme,    3999.98, 'completed', 'North America', '2025-04-02 09:00:00+00', '2025-04-04 13:00:00+00'),
('00000000-0000-4000-a000-000000000023', c_gamma,    899.97, 'completed', 'Europe',        '2025-04-09 08:00:00+00', '2025-04-11 10:00:00+00'),
('00000000-0000-4000-a000-000000000024', c_nu,       299.98, 'completed', 'Latin America', '2025-04-14 14:00:00+00', '2025-04-16 16:00:00+00'),
('00000000-0000-4000-a000-000000000025', c_tau,      549.98, 'pending',   'Europe',        '2025-04-22 09:00:00+00', NULL),

-- May 2025
('00000000-0000-4000-a000-000000000026', c_beta,    1199.97, 'completed', 'Europe',        '2025-05-06 10:00:00+00', '2025-05-08 12:00:00+00'),
('00000000-0000-4000-a000-000000000027', c_theta,   2099.98, 'completed', 'Asia Pacific',  '2025-05-09 06:00:00+00', '2025-05-11 08:00:00+00'),
('00000000-0000-4000-a000-000000000028', c_iota,     699.97, 'completed', 'North America', '2025-05-14 13:00:00+00', '2025-05-16 15:00:00+00'),
('00000000-0000-4000-a000-000000000029', c_pi,       499.97, 'completed', 'Europe',        '2025-05-20 09:00:00+00', '2025-05-22 11:00:00+00'),
('00000000-0000-4000-a000-000000000030', c_sigma,    149.99, 'cancelled', 'Europe',        '2025-05-27 11:00:00+00', NULL),

-- June 2025
('00000000-0000-4000-a000-000000000031', c_lambda,  1299.98, 'completed', 'North America', '2025-06-03 09:00:00+00', '2025-06-05 12:00:00+00'),
('00000000-0000-4000-a000-000000000032', c_omicron, 2299.98, 'completed', 'North America', '2025-06-10 10:00:00+00', '2025-06-12 14:00:00+00'),
('00000000-0000-4000-a000-000000000033', c_rho,     2499.98, 'completed', 'Europe',        '2025-06-17 08:00:00+00', '2025-06-19 10:00:00+00'),
('00000000-0000-4000-a000-000000000034', c_kappa,    999.95, 'processing','Asia Pacific',  '2025-06-23 06:00:00+00', NULL),
('00000000-0000-4000-a000-000000000035', c_eps,      299.98, 'completed', 'North America', '2025-06-28 15:00:00+00', '2025-06-30 17:00:00+00'),

-- July 2025
('00000000-0000-4000-a000-000000000036', c_acme,    3749.98, 'completed', 'North America', '2025-07-07 09:00:00+00', '2025-07-09 14:00:00+00'),
('00000000-0000-4000-a000-000000000037', c_gamma,    599.96, 'completed', 'Europe',        '2025-07-11 08:00:00+00', '2025-07-13 10:00:00+00'),
('00000000-0000-4000-a000-000000000038', c_xi,       449.98, 'completed', 'Asia Pacific',  '2025-07-16 05:00:00+00', '2025-07-18 08:00:00+00'),
('00000000-0000-4000-a000-000000000039', c_mu,      1499.99, 'pending',   'Asia Pacific',  '2025-07-24 04:00:00+00', NULL),

-- August 2025
('00000000-0000-4000-a000-000000000040', c_beta,    3499.98, 'completed', 'Europe',        '2025-08-05 10:00:00+00', '2025-08-07 12:00:00+00'),
('00000000-0000-4000-a000-000000000041', c_theta,    799.98, 'completed', 'Asia Pacific',  '2025-08-12 06:00:00+00', '2025-08-14 08:00:00+00'),
('00000000-0000-4000-a000-000000000042', c_iota,     649.97, 'completed', 'North America', '2025-08-18 13:00:00+00', '2025-08-20 15:00:00+00'),
('00000000-0000-4000-a000-000000000043', c_delta,   1299.99, 'processing','Europe',        '2025-08-25 09:00:00+00', NULL),
('00000000-0000-4000-a000-000000000044', c_upsilon,  199.98, 'completed', 'North America', '2025-08-29 14:00:00+00', '2025-08-31 16:00:00+00'),

-- September 2025
('00000000-0000-4000-a000-000000000045', c_acme,    2999.99, 'completed', 'North America', '2025-09-04 09:00:00+00', '2025-09-06 13:00:00+00'),
('00000000-0000-4000-a000-000000000046', c_lambda,  3299.98, 'completed', 'North America', '2025-09-10 10:00:00+00', '2025-09-12 14:00:00+00'),
('00000000-0000-4000-a000-000000000047', c_pi,       699.97, 'completed', 'Europe',        '2025-09-16 08:00:00+00', '2025-09-18 10:00:00+00'),
('00000000-0000-4000-a000-000000000048', c_nu,       449.98, 'pending',   'Latin America', '2025-09-22 14:00:00+00', NULL),
('00000000-0000-4000-a000-000000000049', c_sigma,    399.97, 'cancelled', 'Europe',        '2025-09-26 11:00:00+00', NULL),

-- October 2025
('00000000-0000-4000-a000-000000000050', c_omicron, 3999.98, 'completed', 'North America', '2025-10-03 09:00:00+00', '2025-10-05 12:00:00+00'),
('00000000-0000-4000-a000-000000000051', c_beta,    1999.98, 'completed', 'Europe',        '2025-10-09 10:00:00+00', '2025-10-11 13:00:00+00'),
('00000000-0000-4000-a000-000000000052', c_gamma,   2099.97, 'completed', 'Europe',        '2025-10-15 08:00:00+00', '2025-10-17 10:00:00+00'),
('00000000-0000-4000-a000-000000000053', c_rho,      799.97, 'processing','Europe',        '2025-10-22 09:00:00+00', NULL),
('00000000-0000-4000-a000-000000000054', c_kappa,   1049.97, 'completed', 'Asia Pacific',  '2025-10-28 06:00:00+00', '2025-10-30 08:00:00+00'),

-- November 2025
('00000000-0000-4000-a000-000000000055', c_acme,    2799.97, 'completed', 'North America', '2025-11-04 09:00:00+00', '2025-11-06 14:00:00+00'),
('00000000-0000-4000-a000-000000000056', c_theta,   3749.98, 'completed', 'Asia Pacific',  '2025-11-10 06:00:00+00', '2025-11-12 08:00:00+00'),
('00000000-0000-4000-a000-000000000057', c_tau,     2499.98, 'completed', 'Europe',        '2025-11-17 10:00:00+00', '2025-11-19 12:00:00+00'),
('00000000-0000-4000-a000-000000000058', c_iota,     699.96, 'completed', 'North America', '2025-11-21 13:00:00+00', '2025-11-23 15:00:00+00'),
('00000000-0000-4000-a000-000000000059', c_eps,      549.97, 'pending',   'North America', '2025-11-26 15:00:00+00', NULL),

-- December 2025
('00000000-0000-4000-a000-000000000060', c_lambda,  3999.98, 'completed', 'North America', '2025-12-02 09:00:00+00', '2025-12-04 13:00:00+00'),
('00000000-0000-4000-a000-000000000061', c_gamma,   1799.97, 'processing','Europe',        '2025-12-09 08:00:00+00', NULL),
('00000000-0000-4000-a000-000000000062', c_upsilon,  299.99, 'completed', 'North America', '2025-12-15 14:00:00+00', '2025-12-17 16:00:00+00')

ON CONFLICT DO NOTHING;

-- ── Order Items ───────────────────────────────────────────────────────────────

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
-- Q4 2024 orders
('00000000-0000-4000-a000-000000000001', p_hw1, 2, 1999.99), ('00000000-0000-4000-a000-000000000001', p_sw1, 1, 299.99),
('00000000-0000-4000-a000-000000000002', p_sv2, 1, 1499.99),
('00000000-0000-4000-a000-000000000003', p_sc2, 1, 1299.99),
('00000000-0000-4000-a000-000000000004', p_sw3, 2, 499.99), ('00000000-0000-4000-a000-000000000004', p_sw2, 1, 199.99),
('00000000-0000-4000-a000-000000000005', p_sw1, 2, 299.99), ('00000000-0000-4000-a000-000000000005', p_an2, 1, 149.99),

-- January 2025
('00000000-0000-4000-a000-000000000006', p_sw1, 2, 299.99), ('00000000-0000-4000-a000-000000000006', p_sv2, 1, 1499.99),
('00000000-0000-4000-a000-000000000007', p_hw1, 1, 1999.99),
('00000000-0000-4000-a000-000000000008', p_sw3, 2, 499.99),
('00000000-0000-4000-a000-000000000009', p_sc2, 1, 1299.99), ('00000000-0000-4000-a000-000000000009', p_sc1, 1, 799.99),
('00000000-0000-4000-a000-000000000010', p_sw4, 5, 99.99),

-- February 2025
('00000000-0000-4000-a000-000000000011', p_sv3, 1, 2999.99), ('00000000-0000-4000-a000-000000000011', p_sv1, 1, 999.99),
('00000000-0000-4000-a000-000000000012', p_sw3, 1, 499.99), ('00000000-0000-4000-a000-000000000012', p_sw2, 2, 199.99),
('00000000-0000-4000-a000-000000000013', p_sv2, 2, 1499.99),
('00000000-0000-4000-a000-000000000014', p_hw2, 1, 399.99), ('00000000-0000-4000-a000-000000000014', p_hw3, 3, 149.99),
('00000000-0000-4000-a000-000000000015', p_sw1, 2, 299.99), ('00000000-0000-4000-a000-000000000015', p_an2, 1, 149.99),

-- March 2025
('00000000-0000-4000-a000-000000000016', p_hw1, 1, 1999.99), ('00000000-0000-4000-a000-000000000016', p_sw1, 1, 299.99),
('00000000-0000-4000-a000-000000000017', p_an2, 3, 149.99),
('00000000-0000-4000-a000-000000000018', p_sw1, 1, 299.99), ('00000000-0000-4000-a000-000000000018', p_an2, 2, 149.99),
('00000000-0000-4000-a000-000000000019', p_an1, 2, 349.99),
('00000000-0000-4000-a000-000000000020', p_sw2, 2, 199.99), ('00000000-0000-4000-a000-000000000020', p_sw4, 1, 99.99),
('00000000-0000-4000-a000-000000000021', p_an1, 1, 349.99),

-- April 2025
('00000000-0000-4000-a000-000000000022', p_sv2, 1, 1499.99), ('00000000-0000-4000-a000-000000000022', p_sc3, 1, 2499.99),
('00000000-0000-4000-a000-000000000023', p_sw1, 3, 299.99),
('00000000-0000-4000-a000-000000000024', p_hw3, 2, 149.99),
('00000000-0000-4000-a000-000000000025', p_hw2, 1, 399.99), ('00000000-0000-4000-a000-000000000025', p_an2, 1, 149.99),

-- May 2025
('00000000-0000-4000-a000-000000000026', p_sw3, 2, 499.99), ('00000000-0000-4000-a000-000000000026', p_sw2, 1, 199.99),
('00000000-0000-4000-a000-000000000027', p_sc2, 1, 1299.99), ('00000000-0000-4000-a000-000000000027', p_sc1, 1, 799.99),
('00000000-0000-4000-a000-000000000028', p_sw1, 2, 299.99), ('00000000-0000-4000-a000-000000000028', p_sw4, 1, 99.99),
('00000000-0000-4000-a000-000000000029', p_sw2, 1, 199.99), ('00000000-0000-4000-a000-000000000029', p_an2, 2, 149.99),
('00000000-0000-4000-a000-000000000030', p_hw3, 1, 149.99),

-- June 2025
('00000000-0000-4000-a000-000000000031', p_sw3, 1, 499.99), ('00000000-0000-4000-a000-000000000031', p_sc1, 1, 799.99),
('00000000-0000-4000-a000-000000000032', p_hw1, 1, 1999.99), ('00000000-0000-4000-a000-000000000032', p_sw1, 1, 299.99),
('00000000-0000-4000-a000-000000000033', p_sv1, 1, 999.99), ('00000000-0000-4000-a000-000000000033', p_sv2, 1, 1499.99),
('00000000-0000-4000-a000-000000000034', p_an1, 2, 349.99), ('00000000-0000-4000-a000-000000000034', p_sw4, 3, 99.99),
('00000000-0000-4000-a000-000000000035', p_an2, 2, 149.99),

-- July 2025
('00000000-0000-4000-a000-000000000036', p_sc2, 1, 1299.99), ('00000000-0000-4000-a000-000000000036', p_sc3, 1, 2449.99),
('00000000-0000-4000-a000-000000000037', p_sw2, 2, 199.99), ('00000000-0000-4000-a000-000000000037', p_sw4, 2, 99.99),
('00000000-0000-4000-a000-000000000038', p_sw1, 1, 299.99), ('00000000-0000-4000-a000-000000000038', p_hw3, 1, 149.99),
('00000000-0000-4000-a000-000000000039', p_sv2, 1, 1499.99),

-- August 2025
('00000000-0000-4000-a000-000000000040', p_hw1, 1, 1999.99), ('00000000-0000-4000-a000-000000000040', p_sv2, 1, 1499.99),
('00000000-0000-4000-a000-000000000041', p_sw3, 1, 499.99), ('00000000-0000-4000-a000-000000000041', p_sw1, 1, 299.99),
('00000000-0000-4000-a000-000000000042', p_an1, 1, 349.99), ('00000000-0000-4000-a000-000000000042', p_an2, 2, 149.99),
('00000000-0000-4000-a000-000000000043', p_sc2, 1, 1299.99),
('00000000-0000-4000-a000-000000000044', p_sw4, 2, 99.99),

-- September 2025
('00000000-0000-4000-a000-000000000045', p_sv3, 1, 2999.99),
('00000000-0000-4000-a000-000000000046', p_sc3, 1, 2499.99), ('00000000-0000-4000-a000-000000000046', p_sc1, 1, 799.99),
('00000000-0000-4000-a000-000000000047', p_sw3, 1, 499.99), ('00000000-0000-4000-a000-000000000047', p_sw4, 2, 99.99),
('00000000-0000-4000-a000-000000000048', p_sw1, 1, 299.99), ('00000000-0000-4000-a000-000000000048', p_an2, 1, 149.99),
('00000000-0000-4000-a000-000000000049', p_hw3, 2, 149.99), ('00000000-0000-4000-a000-000000000049', p_sw4, 1, 99.99),

-- October 2025
('00000000-0000-4000-a000-000000000050', p_hw1, 2, 1999.99),
('00000000-0000-4000-a000-000000000051', p_sw3, 1, 499.99), ('00000000-0000-4000-a000-000000000051', p_sv2, 1, 1499.99),
('00000000-0000-4000-a000-000000000052', p_sc2, 1, 1299.99), ('00000000-0000-4000-a000-000000000052', p_hw2, 2, 399.99),
('00000000-0000-4000-a000-000000000053', p_sw1, 2, 299.99), ('00000000-0000-4000-a000-000000000053', p_sw2, 1, 199.99),
('00000000-0000-4000-a000-000000000054', p_an1, 3, 349.99),

-- November 2025
('00000000-0000-4000-a000-000000000055', p_hw1, 1, 1999.99), ('00000000-0000-4000-a000-000000000055', p_sw3, 1, 499.99), ('00000000-0000-4000-a000-000000000055', p_sw1, 1, 299.99),
('00000000-0000-4000-a000-000000000056', p_sc3, 1, 2499.99), ('00000000-0000-4000-a000-000000000056', p_sc2, 1, 1299.99),
('00000000-0000-4000-a000-000000000057', p_sv2, 1, 1499.99), ('00000000-0000-4000-a000-000000000057', p_sv1, 1, 999.99),
('00000000-0000-4000-a000-000000000058', p_sw2, 2, 199.99), ('00000000-0000-4000-a000-000000000058', p_an2, 2, 149.99),
('00000000-0000-4000-a000-000000000059', p_an1, 1, 349.99), ('00000000-0000-4000-a000-000000000059', p_sw4, 2, 99.99),

-- December 2025
('00000000-0000-4000-a000-000000000060', p_sv3, 1, 2999.99), ('00000000-0000-4000-a000-000000000060', p_sv1, 1, 999.99),
('00000000-0000-4000-a000-000000000061', p_sw3, 2, 499.99), ('00000000-0000-4000-a000-000000000061', p_sc1, 1, 799.99),
('00000000-0000-4000-a000-000000000062', p_sw1, 1, 299.99)

ON CONFLICT DO NOTHING;

END $$;
