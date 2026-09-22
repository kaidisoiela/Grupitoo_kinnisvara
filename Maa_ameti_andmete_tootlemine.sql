CREATE SCHEMA IF NOT exists Grupitoo_KV;


/* JUHEND: Tekkinud uue Schemas (vasakul) all tee paremkliki "Tables" peal ning "import data". Vali git kaustas fail "maa_amet_py_final.csv" */

drop table Fact_KV;

create table grupitoo_kv.Fact_KV AS
	select
		 CASE 
        WHEN SPLIT_PART(quarter, ' ', 2) = 'I'   THEN (SPLIT_PART(quarter, ' ', 1) || '-01-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'II'  THEN (SPLIT_PART(quarter, ' ', 1) || '-04-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'III' THEN (SPLIT_PART(quarter, ' ', 1) || '-07-01')::DATE
        WHEN SPLIT_PART(quarter, ' ', 2) = 'IV'  THEN (SPLIT_PART(quarter, ' ', 1) || '-10-01')::DATE
    	END AS FK_quarter_ID,
		county as FK_county_ID,
		transaction_count::integer,
		total_area_ha::numeric(20,2),
		total_value_eur::numeric(20,2),
		round(total_value_eur/(total_area_ha/10000), 2) as value_per_m2,
		round(total_value_eur/transaction_count::integer, 2) as value_per_transaction
	from grupitoo_kv.maa_amet_py_final;



		