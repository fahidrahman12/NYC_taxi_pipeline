-- Standardises green taxi raw data using the same column contract as stg_yellow_taxi
-- so both can be unioned cleanly in the fact layer.
-- Green taxis have a trip_type column (street-hail vs dispatch) that yellow lacks;
-- yellow's airport_fee column is absent from green — both are handled with nulls.

with source as (
    select * from {{ source('raw', 'green_taxi_trips') }}
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
        cast(lpep_pickup_datetime  as TIMESTAMP) as pickup_datetime,
        cast(lpep_dropoff_datetime as TIMESTAMP) as dropoff_datetime,

        -- trip metrics
        cast(passenger_count    as INT64)   as passenger_count,
        cast(trip_distance      as FLOAT64) as trip_distance_miles,
        cast(trip_type          as INT64)   as trip_type,      -- green-only

        -- financials
        cast(fare_amount            as NUMERIC) as fare_amount,
        cast(extra                  as NUMERIC) as extra,
        cast(mta_tax                as NUMERIC) as mta_tax,
        cast(tip_amount             as NUMERIC) as tip_amount,
        cast(tolls_amount           as NUMERIC) as tolls_amount,
        cast(improvement_surcharge  as NUMERIC) as improvement_surcharge,
        cast(congestion_surcharge   as NUMERIC) as congestion_surcharge,
        cast(null                   as NUMERIC) as airport_fee,  -- not applicable for green
        cast(total_amount           as NUMERIC) as total_amount,

        -- flags
        store_and_fwd_flag,

        -- discriminator
        'green' as taxi_type

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
