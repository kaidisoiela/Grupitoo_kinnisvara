CREATE SCHEMA IF NOT exists Grupitoo_KV;

DROP TABLE IF EXISTS grupitoo_kv.maa_amet_py_final CASCADE;

CREATE TABLE grupitoo_kv.maa_amet_py_final (
    quarter VARCHAR(50),
    county VARCHAR(100),
    transaction_count INTEGER,
    avg_price_m2 NUMERIC(20,4)
);


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
		avg_price_m2::numeric(20)
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



/* JUHEND: Tekkinud uue Schemas (vasakul) all tee paremkliki "Tables" peal ning "import data". Vali git kaustas fail "Eesti_keskmine_palk_maakonniti_2005_2025_py_final.csv" */

-- 1. Kustutame vana tabeli, kui see on olemas
DROP TABLE IF EXISTS grupitoo_kv.fact_palk CASCADE;

-- 2. Loome esialgse Fact_PALK tabeli koos kõigi andmetulpadega (sh palk / salary)
CREATE TABLE grupitoo_kv.fact_palk AS
SELECT
    CASE 
        WHEN SPLIT_PART(quarter, ' ', 2) = 'I'   THEN (SPLIT_PART(quarter, ' ', 1) || '-01-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'II'  THEN (SPLIT_PART(quarter, ' ', 1) || '-04-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'III' THEN (SPLIT_PART(quarter, ' ', 1) || '-07-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'IV'  THEN (SPLIT_PART(quarter, ' ', 1) || '-10-01')::DATE
    END AS FK_quarter_ID,
    county AS county_name,
    salary AS average_salary -- Lisatud sisendtabeli palga veerg
FROM grupitoo_kv.Eesti_keskmine_palk_maakonniti;

-- 3. SEOSETE LOOMINE: Järgime täpselt Sinu näidatud Fact_KV loogikat

-- Samm A: Lisame Fact_PALK tabelisse uue tühja maakonna ID veeru
ALTER TABLE grupitoo_kv.fact_palk 
ADD COLUMN FK_county_id INTEGER;

-- Samm B: Uuendame ID väärtused Dim_County tabeli põhjal, ühitades nimed
UPDATE grupitoo_kv.fact_palk AS f
SET FK_county_id = c.PK_county_ID
FROM grupitoo_kv.Dim_County c
WHERE f.county_name = c.county_name;

-- Samm C: Eemaldame nüüd ülearuseks muutunud tekstipõhise maakonna nime veeru
ALTER TABLE grupitoo_kv.fact_palk DROP COLUMN county_name;

-- Samm D: Määrame andmetüüpidele rangemad piirangud (andmeterviklikkus)
ALTER TABLE grupitoo_kv.fact_palk 
    ALTER COLUMN FK_quarter_ID SET NOT NULL,
    ALTER COLUMN FK_county_id SET NOT NULL;

-- Samm E: Lisame välisvõtme (Foreign Key) seose County dimensiooniga
ALTER TABLE grupitoo_kv.fact_palk 
ADD CONSTRAINT FK_Fact_PALK_county 
FOREIGN KEY (FK_county_id) REFERENCES grupitoo_kv.Dim_County(PK_county_ID);

-- Samm F: Lisame välisvõtme (Foreign Key) seose Time dimensiooniga
ALTER TABLE grupitoo_kv.fact_palk 
ADD CONSTRAINT FK_Fact_PALK_time 
FOREIGN KEY (FK_quarter_ID) REFERENCES grupitoo_kv.Dim_Time(PK_quarter_ID);

-- 4. KONTROLLPÄRING: Vaatame, kas andmed ja ID-d said korrektselt paika
SELECT * FROM grupitoo_kv.fact_palk ORDER BY FK_quarter_ID, FK_county_id LIMIT 10;



--Intressimäärade tabeli lisamine ja ühendamine


/* JUHEND: Tekkinud uue Schemas (vasakul) all tee paremkliki "Tables" peal ning "import data". Vali git kaustas fail "puhastatud_eluasemelaenud_py_final.csv" */


DROP TABLE IF exists grupitoo_kv.intressid_kv;

create table grupitoo_kv.intressid_kv as
SELECT 
    kuupaev,
    valuuta,
    intressimaar_laenusummalt,
    -- Muudame teksti kuupäevaks ja arvutame kvartali alguse
    DATE_TRUNC('quarter', kuupaev::DATE)::DATE AS FK_quarter_ID
FROM grupitoo_kv.puhastatud_eluasemelaenud_py_final;



DROP TABLE IF exists grupitoo_kv.Fact_intressid;

create table grupitoo_kv.Fact_intressid as
SELECT 
	FK_quarter_ID,
    avg(intressimaar_laenusummalt)::numeric(10,2) as intress
FROM grupitoo_kv.intressid_kv
where valuuta='EUR' and FK_quarter_ID < DATE '2026-07-01'
group by FK_quarter_ID;


-- Lisame välisvõtme (Foreign Key) seose Time dimensiooniga

ALTER TABLE grupitoo_kv.Fact_intressid
ADD CONSTRAINT FK_Fact_intress_time 
FOREIGN KEY (FK_quarter_ID) REFERENCES grupitoo_kv.Dim_Time(PK_quarter_ID);

--THI tabeli lisamine ja ühendamine


/* JUHEND: Tekkinud uue Schemas (vasakul) all tee paremkliki "Tables" peal ning "import data". Vali git kaustas fail "thi_py_final.csv" */


-- 1. Kustutame vana fact_thi tabeli, kui see on olemas
DROP TABLE IF EXISTS grupitoo_kv.fact_thi CASCADE;

-- 2. Loome uue faktitabeli võttes andmed Sinu tabelist thi_py_final
CREATE TABLE grupitoo_kv.fact_thi AS
SELECT 
    quarter_id::DATE as FK_quarter_ID,
    keskmine_indeks
FROM grupitoo_kv.thi_py_final
where quarter_id::DATE < DATE '2026-07-01';


-- 3. Lisame välisvõtme seose Dim_Time dimensiooniga
ALTER TABLE grupitoo_kv.fact_thi
ADD CONSTRAINT FK_Fact_thi_time 
FOREIGN KEY (FK_quarter_ID) REFERENCES grupitoo_kv.Dim_Time(PK_quarter_ID);

