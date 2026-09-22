CREATE SCHEMA IF NOT exists Grupitoo_KV;

create table intressid_kv as
SELECT 
    kuupaev,
    valuuta,
    intressimaar_laenusummalt,
    -- Muudame teksti kuupäevaks ja arvutame kvartali alguse
    DATE_TRUNC('quarter', kuupaev::DATE)::DATE AS FK_quarter_ID
FROM puhastatud_eluasemelaenud_py_final;


DROP TABLE IF exists intressid_py_final;

create table intressid_py_final as
SELECT 
	FK_quarter_ID,
    avg(intressimaar_laenusummalt)::numeric(3,2) as intress
FROM intressid_kv
where valuuta='EUR'
group by FK_quarter_ID;


