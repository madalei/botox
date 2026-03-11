--
-- PostgreSQL database dump
--

\restrict h5MVbdrsU2CVSvs4hXcSIbrX1NWerhVH8xcqT3Gehv44U9NcJkAqJq1HQj04Ffm

-- Dumped from database version 14.20 (Homebrew)
-- Dumped by pg_dump version 14.20 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bot_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bot_logs (
    id bigint NOT NULL,
    bot_id text,
    level text NOT NULL,
    message text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: bot_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bot_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bot_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bot_logs_id_seq OWNED BY public.bot_logs.id;


--
-- Name: bots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bots (
    id text NOT NULL,
    strategy text NOT NULL,
    params jsonb NOT NULL,
    status text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    bot_id text,
    symbol text NOT NULL,
    side text NOT NULL,
    price numeric NOT NULL,
    executed_at timestamp with time zone,
    created_at timestamp with time zone,
    stop_loss numeric,
    take_profit numeric,
    amount numeric NOT NULL,
    status text
);


--
-- Name: bot_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_logs ALTER COLUMN id SET DEFAULT nextval('public.bot_logs_id_seq'::regclass);


--
-- Name: bot_logs bot_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_logs
    ADD CONSTRAINT bot_logs_pkey PRIMARY KEY (id);


--
-- Name: bots bots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bots
    ADD CONSTRAINT bots_pkey PRIMARY KEY (id);


--
-- Name: orders trades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT trades_pkey PRIMARY KEY (id);


--
-- Name: bot_logs bot_logs_bot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_logs
    ADD CONSTRAINT bot_logs_bot_id_fkey FOREIGN KEY (bot_id) REFERENCES public.bots(id) ON DELETE CASCADE;


--
-- Name: orders trades_bot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT trades_bot_id_fkey FOREIGN KEY (bot_id) REFERENCES public.bots(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict h5MVbdrsU2CVSvs4hXcSIbrX1NWerhVH8xcqT3Gehv44U9NcJkAqJq1HQj04Ffm

