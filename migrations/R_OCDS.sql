CREATE INDEX "view_data_dncp_data.idx_item_classification" ON view_data_dncp_data.award_items_summary (item_classification);

DROP MATERIALIZED VIEW view_data_dncp_data.unique_suppliers;
CREATE MATERIALIZED VIEW view_data_dncp_data.unique_suppliers AS
(
SELECT DISTINCT parties_summary.party ->> 'name'::text                                   AS name,
                replace(parties_summary.party ->> 'id'::text, 'PY-RUC-'::text, ''::text) AS ruc,
                regexp_replace((parties_summary.party -> 'contactPoint'::text) ->> 'telephone'::text, '[^0-9]+'::text,
                               ''::text, 'g'::text)                                      AS telephone,
                (parties_summary.party -> 'contactPoint'::text) ->> 'name'::text         AS contact_point,
                (parties_summary.party -> 'address'::text) ->> 'countryName'::text       AS pais,
                upper((parties_summary.party -> 'address'::text) ->> 'region'::text)     AS departamento,
                upper((parties_summary.party -> 'address'::text) ->> 'locality'::text)   AS ciudad,
                (parties_summary.party -> 'address'::text) ->> 'streetAddress'::text     AS direccion
FROM view_data_collection_3.parties_summary
WHERE NOT parties_summary.roles ? 'buyer'::text
  AND NOT parties_summary.roles ? 'procuringEntity'::text
  AND NOT parties_summary.roles ? 'payer'::text
  AND parties_summary.parties_id ~~ 'PY-RUC-%'::text );


alter table view_data_dncp_data.tender_summary add column tender_datepublished  timestamp;
  alter table view_data_dncp_data.tender_summary add column covid  boolean default false;

 update view_data_dncp_data.tender_summary ts
set tender_datepublished = (
    select max(t.tender->>'datePublished')::timestamp
    from view_data_dncp_data.tender_summary_with_data t
    where t.ocid = ts.ocid and t.data_id = ts.data_id
    );

update view_data_dncp_data.tender_summary ts
set covid = (
    select  case when t.tender->'coveredBy' ? 'covid_19' is null then false else t.tender->'coveredBy' ? 'covid_19' end
    from view_data_dncp_data.tender_summary_with_data t
    where t.ocid = ts.ocid and t.data_id = ts.data_id
    );


create or replace function get_promedio_before_covid(presentacion text, moneda text, catalogo_n5 text, unidad text)
    RETURNS integer AS $$
        BEGIN
    return
    avg(ai.unit_amount) as precio_unitario_promedio_antes_pandemia
    from view_data_dncp_data.award_items_summary ai
    join view_data_dncp_data.tender_summary t on ai.ocid = t.ocid
    where ai.item_classification = catalogo_n5 and ai.item->'attributes'->1->>'value' = presentacion
    and ai.item->'unit'->>'name' = unidad and ai.unit_currency = moneda
    and t.tender_datepublished < '2020-03-01';

            END;
$$ LANGUAGE plpgsql;

alter table view_data_dncp_data.awards_summary_no_data add column fecha_firma_contrato timestamp;
update view_data_dncp_data.awards_summary_no_data a
set fecha_firma_contrato = c.datesigned
from view_data_dncp_data.contracts_summary_no_data c where c.data_id = a.data_id and c.award_id = a.award_id;

set search_path to view_data_dncp_data, public;

create or  replace function get_max_collection() returns integer
    language sql
as
$$
     select max(id) from selected_collections;
$$;
create or  replace function get_duplicated_ids() returns setof int
    language sql
as
$$
select distinct data_id from release_summary r
where collection_id < get_max_collection() and ocid in (select distinct ocid
    from release_summary  rr where collection_id = get_max_collection());
$$;

delete from record where data_id in (
select * from get_duplicated_ids());

delete from data where id in (
select * from get_duplicated_ids());

delete from tender_documents_summary where data_id in (
select * from get_duplicated_ids());

delete from tender_items_summary where data_id in (
select * from get_duplicated_ids());

delete from procuringentity_summary where data_id in (
select * from get_duplicated_ids());

delete from tenderers_summary where data_id in (
select * from get_duplicated_ids());

delete from tender_summary where data_id in (
select * from get_duplicated_ids());

delete from buyer_summary where data_id in (
select * from get_duplicated_ids());


delete from planning_summary where data_id in (
select * from get_duplicated_ids());

delete from parties_summary_no_data where data_id in (
select * from get_duplicated_ids());

delete from award_suppliers_summary where data_id in (
select * from get_duplicated_ids());

delete from award_items_summary where data_id in (
select * from get_duplicated_ids());

delete from award_documents_summary where data_id in (
select * from get_duplicated_ids());

delete from awards_summary_no_data where data_id in (
select * from get_duplicated_ids());

delete from contract_documents_summary where data_id in (
select * from get_duplicated_ids());

delete from contract_implementation_documents_summary where data_id in (
select * from get_duplicated_ids());

delete from contract_implementation_milestones_summary where data_id in (
select * from get_duplicated_ids());

delete from contract_implementation_transactions_summary where data_id in (
select * from get_duplicated_ids());

delete from contract_items_summary where data_id in (
select * from get_duplicated_ids());

delete from contract_milestones_summary where data_id in (
select * from get_duplicated_ids());

delete from contracts_summary_no_data where data_id in (
select * from get_duplicated_ids());


delete from release_summary where data_id in (
select * from get_duplicated_ids());
