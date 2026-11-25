-- =============================================================
-- 01_create_schema.sql
-- Creates the practice database and its five tables.
-- Safe to re-run: it drops and rebuilds everything.
-- All data in this project is invented. No real dealership data.
-- =============================================================

DROP DATABASE IF EXISTS dealer_practice;
CREATE DATABASE dealer_practice;
USE dealer_practice;

-- One row per dealership location ("rooftop")
CREATE TABLE rooftops (
    rooftop_id   INT          PRIMARY KEY,
    name         VARCHAR(60)  NOT NULL,
    brand        VARCHAR(30)  NOT NULL,   -- e.g. Ford, Toyota
    market       VARCHAR(30)  NOT NULL,   -- Buffalo, Rochester, Syracuse
    is_luxury    TINYINT(1)   NOT NULL DEFAULT 0,
    opened_date  DATE         NOT NULL
);

-- One row per person. Contains planted duplicates on purpose
-- (same person entered twice with small differences) for cleanup practice.
CREATE TABLE customers (
    customer_id  INT          PRIMARY KEY,
    first_name   VARCHAR(40)  NOT NULL,
    last_name    VARCHAR(40)  NOT NULL,
    email        VARCHAR(100),
    phone        VARCHAR(20),
    zip          CHAR(5),
    created_date DATE         NOT NULL
);

-- One row per vehicle that has ever been in stock.
-- status = 'in_stock' or 'sold'
CREATE TABLE vehicles (
    vin          CHAR(17)     PRIMARY KEY,
    rooftop_id   INT          NOT NULL,
    new_used     VARCHAR(4)   NOT NULL,   -- 'New' or 'Used'
    model_year   SMALLINT     NOT NULL,
    make         VARCHAR(30)  NOT NULL,
    model        VARCHAR(40)  NOT NULL,
    mileage      INT          NOT NULL,
    stock_date   DATE         NOT NULL,
    cost         DECIMAL(10,2) NOT NULL,
    list_price   DECIMAL(10,2) NOT NULL,
    status       VARCHAR(10)  NOT NULL,
    FOREIGN KEY (rooftop_id) REFERENCES rooftops(rooftop_id)
);

-- One row per vehicle sale
-- deal_type = 'Cash', 'Finance' or 'Lease'
-- front_gross = sale_price - vehicle cost
CREATE TABLE deals (
    deal_id      INT          PRIMARY KEY,
    vin          CHAR(17)     NOT NULL,
    customer_id  INT          NOT NULL,
    rooftop_id   INT          NOT NULL,
    salesperson  VARCHAR(40)  NOT NULL,
    sold_date    DATE         NOT NULL,
    deal_type    VARCHAR(10)  NOT NULL,
    sale_price   DECIMAL(10,2) NOT NULL,
    front_gross  DECIMAL(10,2) NOT NULL,
    back_gross   DECIMAL(10,2) NOT NULL,  -- F&I products, reserve
    FOREIGN KEY (vin)         REFERENCES vehicles(vin),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (rooftop_id)  REFERENCES rooftops(rooftop_id)
);

-- One row per service repair order (RO)
-- pay_type = 'Customer' (customer pays) or 'Warranty' (manufacturer pays)
CREATE TABLE service_ros (
    ro_id        INT          PRIMARY KEY,
    vin          CHAR(17)     NOT NULL,
    customer_id  INT          NOT NULL,
    rooftop_id   INT          NOT NULL,
    ro_date      DATE         NOT NULL,
    pay_type     VARCHAR(10)  NOT NULL,
    labor_total  DECIMAL(10,2) NOT NULL,
    parts_total  DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (vin)         REFERENCES vehicles(vin),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (rooftop_id)  REFERENCES rooftops(rooftop_id)
);
