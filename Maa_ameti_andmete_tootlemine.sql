CREATE SCHEMA IF NOT exists Grupitoo_KV;


/* JUHEND: Tekkinud uue Schemas (vasakul) all tee paremkliki "Tables" peal ning "import data". Vali git kaustas fail "maa_amet_py_final.csv" */

--- Teeme Fact_KV tabeli:

DROP TABLE IF EXISTS grupitoo_kv.fact_kv;

create table grupitoo_kv.fact_kv AS
	select
		 CASE 
        	WHEN SPLIT_PART(quarter, ' ', 2) = 'I'   THEN (SPLIT_PART(quarter, ' ', 1) || '-01-01')::DATE
        	WHEN SPLIT_PART(quarter, ' ', 2) = 'II'  THEN (SPLIT_PART(quarter, ' ', 1) || '-04-01')::DATE
        	WHEN SPLIT_PART(quarter, ' ', 2) = 'III' THEN (SPLIT_PART(quarter, ' ', 1) || '-07-01')::DATE
        	WHEN SPLIT_PART(quarter, ' ', 2) = 'IV'  THEN (SPLIT_PART(quarter, ' ', 1) || '-10-01')::DATE
    	END AS FK_quarter_ID,
		county as county_name,
		transaction_count::INTEGER,
		total_area_ha::numeric(20,2),
		total_value_eur::numeric(20,2),
		round(total_value_eur::numeric / nullif(total_area_ha::numeric * 100000, 0), 2) as value_per_m2,
		round(total_value_eur::numeric / transaction_count::integer, 2) as value_per_transaction
	from grupitoo_kv.maa_amet_py_final;


--- Teeme Dim_County tabeli:

DROP TABLE IF EXISTS grupitoo_kv.Dim_County CASCADE;

CREATE TABLE grupitoo_kv.Dim_County (
    PK_county_ID SERIAL PRIMARY KEY,
    county_name VARCHAR(100) UNIQUE NOT NULL
);

-- Täidame tabeli unikaalsete maakondadega
INSERT INTO grupitoo_kv.Dim_County (county_name)
SELECT DISTINCT county 
FROM grupitoo_kv.maa_amet_py_final
WHERE county IS NOT NULL
ORDER BY county;



--- Teeme Dim_Time tabeli:

DROP TABLE IF EXISTS grupitoo_kv.Dim_Time CASCADE;

CREATE TABLE grupitoo_kv.Dim_Time (
    PK_quarter_ID DATE PRIMARY KEY,
    year_number INTEGER NOT NULL,
    quarter_number INTEGER NOT NULL,
    quarter_string VARCHAR(10) NOT NULL, -- nt "2024 Q2" või "2024 II"
    half_year INTEGER NOT NULL
);

-- Täidame ajatabeli genereeritud väärtustega faktitabeli kuupäevade põhjal
INSERT INTO grupitoo_kv.Dim_Time (PK_quarter_ID, year_number, quarter_number, quarter_string, half_year)
SELECT DISTINCT
    -- Kasutame sama loogikat, mis faktitabelis kuupäeva saamiseks
    CASE 
        WHEN SPLIT_PART(quarter, ' ', 2) = 'I'   THEN (SPLIT_PART(quarter, ' ', 1) || '-01-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'II'  THEN (SPLIT_PART(quarter, ' ', 1) || '-04-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'III' THEN (SPLIT_PART(quarter, ' ', 1) || '-07-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'IV'  THEN (SPLIT_PART(quarter, ' ', 1) || '-10-01')::DATE
    END AS PK_quarter_ID,
    
    -- Tuletame lisaveerud tekstist
    SPLIT_PART(quarter, ' ', 1)::INTEGER AS year_number,
    
    CASE 
        WHEN SPLIT_PART(quarter, ' ', 2) = 'I'   THEN 1
        WHEN SPLIT_PART(quarter, ' ', 2) = 'II'  THEN 2
        WHEN SPLIT_PART(quarter, ' ', 2) = 'III' THEN 3
        WHEN SPLIT_PART(quarter, ' ', 2) = 'IV'  THEN 4
    END AS quarter_number,
    
    quarter AS quarter_string,
    
    CASE 
        WHEN SPLIT_PART(quarter, ' ', 2) IN ('I', 'II') THEN 1
        ELSE 2
    END AS half_year
FROM grupitoo_kv.maa_amet_py_final
ORDER BY PK_quarter_ID;




--- Ühendame Fact_KV tabeli dim tabelitega


--County dim'iga:

ALTER TABLE grupitoo_kv.Fact_KV 
ADD COLUMN FK_county_id INTEGER;


UPDATE grupitoo_kv.Fact_KV as f
SET FK_county_id = c.PK_county_ID
FROM grupitoo_kv.Dim_County c
WHERE f.county_name = c.county_name;


ALTER TABLE grupitoo_kv.Fact_KV DROP COLUMN county_name;


ALTER TABLE grupitoo_kv.Fact_KV 
ADD CONSTRAINT FK_Fact_county 
FOREIGN KEY (FK_county_ID) REFERENCES grupitoo_kv.Dim_County(PK_county_ID);

--Time dim'iga:

ALTER TABLE grupitoo_kv.Fact_KV 
ADD CONSTRAINT FK_Fact_time 
FOREIGN KEY (FK_quarter_ID) REFERENCES grupitoo_kv.Dim_Time(PK_quarter_ID);

