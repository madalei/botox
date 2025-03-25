CREATE TABLE public.orders (
	id int NOT NULL,
	order_uid varchar NOT NULL,
	operation varchar NOT NULL,
	quantity float4 NULL,
	price float4 NULL,
	total float4 NULL,
	currency varchar NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT orders_pk PRIMARY KEY (id),
	CONSTRAINT orders_unique UNIQUE (order_uid)
);

-- Column comments

COMMENT ON COLUMN public.orders.operation IS 'B for Buy S for Sell';