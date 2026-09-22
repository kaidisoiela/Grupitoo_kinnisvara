CREATE SCHEMA IF NOT exists Grupitoo_KV;

SELECT 
    kuupaev,
    valuuta,
    intressimaar_laenusummalt,
    -- Muudame teksti kuupäevaks ja arvutame kvartali alguse
    DATE_TRUNC('quarter', kuupaev::DATE)::DATE AS FK_quarter_ID
FROM puhastatud_eluasemelaenud_py_final;