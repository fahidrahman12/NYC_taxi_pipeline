with source as (
    select * from {{ source('raw', 'taxi_zones') }}
)

select
    cast(LocationID   as INT64)  as location_id,
    Borough                      as borough,
    Zone                         as zone_name,
    service_zone
from source
where LocationID is not null
