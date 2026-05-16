-- Zone dimension table.
-- Wraps stg_taxi_zones and adds a surrogate key for clean FK relationships.

select
    {{ dbt_utils.generate_surrogate_key(['location_id']) }} as zone_id,
    location_id,
    borough,
    zone_name,
    service_zone
from {{ ref('stg_taxi_zones') }}
