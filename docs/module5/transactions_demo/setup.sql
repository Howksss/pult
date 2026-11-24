DROP TABLE IF EXISTS transfer_log;
DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    id integer PRIMARY KEY,
    owner varchar(100) NOT NULL,
    balance numeric(12, 2) NOT NULL,
    CONSTRAINT accounts_balance_not_negative CHECK (balance >= 0)
);

CREATE TABLE transfer_log (
    id serial PRIMARY KEY,
    from_id integer NOT NULL REFERENCES accounts (id),
    to_id integer NOT NULL REFERENCES accounts (id),
    amount numeric(12, 2) NOT NULL CHECK (amount > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO accounts (id, owner, balance)
VALUES
    (1, 'Пекарня на Мира', 1000.00),
    (2, 'Пекарня на Ленина', 500.00);
