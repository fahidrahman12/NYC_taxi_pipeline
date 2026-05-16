-- Standardises yellow taxi raw data:
--   • Renames columns to snake_case
--   • Casts to canonical types
--   • Filters clearly invalid rows (negative fares, impossible distances)
--   • Adds taxi_type discriminator for downstream unioning

with source as (
    select * from {{ source('raw', 'yellow_taxi_trips') }}
),

cleaned as (
    select
        -- identifiers
        cast(VendorID        as INT64)    as vendor_id,
        cast(RatecodeID      as INT64)    as rate_code_id,
        cast(PULocationID    as INT64)    as pickup_location_id,
        cast(DOLocationID    as INT64)    as dropoff_location_id,
        cast(payment_type    as INT64)    as payment_type_id,

        -- timestamps
        cast(tpep_pickup_datetime  as TIMESTAMP) as pickup_datetime,
        cast(tpep_dropoff_datetime as TIMESTAMP) as dropoff_datetime,

        -- trip metrics
        cast(passenger_count    as INT64)   as passenger_count,
        cast(trip_distance      as FLOAT64) as trip_distance_miles,

        -- financials
        cast(fare_amount            as NUMERIC) as fare_amount,
        cast(extra                  as NUMERIC) as extra,
        cast(mta_tax                as NUMERIC) as mta_tax,
        cast(tip_amount             as NUMERIC) as tip_amount,
        cast(tolls_amount           as NUMERIC) as tolls_amount,
        cast(improvement_surcharge  as NUMERIC) as improvement_surcharge,
        cast(congestion_surcharge   as NUMERIC) as congestion_surcharge,
        cast(airport_fee            as NUMERIC) as airport_fee,
        cast(total_amount           as NUMERIC) as total_amount,

        -- flags
        store_and_fwd_flag,

        -- discriminator
        'yellow' as taxi_type

    from source
),

validated as (
    select *
    from cleaned
    where
        pickup_datetime  is not null
        and dropoff_datetime is not null
        and pickup_datetime < dropoff_datetime
        and trip_distance_miles >= 0
        and fare_amount >= 0
        and total_amount >= 0
        and pickup_location_id is not null
        and dropoff_location_id is not null
)

select * from validated
