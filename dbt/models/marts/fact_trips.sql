{{
    config(
        partition_by={
            "field": "pickup_date",
            "data_type": "date",
            "granularity": "day"
        },
        cluster_by=["taxi_type", "payment_type_id", "pickup_location_id"]
    )
}}

-- Central fact table combining yellow and green taxi trips.
-- Partitioned by pickup_date and clustered for efficient analytical queries.

with yellow as (
    select
        vendor_id,
        rate_code_id,
        pickup_location_id,
        dropoff_location_id,
        payment_type_id,
        pickup_datetime,
        dropoff_datetime,
        passenger_count,
        trip_distance_miles,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        congestion_surcharge,
        airport_fee,
        total_amount,
        store_and_fwd_flag,
        taxi_type,
        null as trip_type    -- green only
    from {{ ref('stg_yellow_taxi') }}
),

green as (
    select
        vendor_id,
        rate_code_id,
        pickup_location_id,
        dropoff_location_id,
        payment_type_id,
        pickup_datetime,
        dropoff_datetime,
        passenger_count,
        trip_distance_miles,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        congestion_surcharge,
        airport_fee,
        total_amount,
        store_and_fwd_flag,
        taxi_type,
        trip_type
    from {{ ref('stg_green_taxi') }}
),

all_trips as (
    select * from yellow
    union all
    select * from green
),

enriched as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'taxi_type',
            'pickup_datetime',
            'dropoff_datetime',
            'pickup_location_id',
            'dropoff_location_id',
            'total_amount'
        ]) }}                                          as trip_id,

        -- dimensions (FKs)
        taxi_type,
        vendor_id,
        rate_code_id,
        payment_type_id,
        pickup_location_id,
        dropoff_location_id,
        trip_type,

        -- timestamps and derived date keys
        pickup_datetime,
        dropoff_datetime,
        date(pickup_datetime)                          as pickup_date,
        extract(year  from pickup_datetime)            as pickup_year,
        extract(month from pickup_datetime)            as pickup_month,
        extract(hour  from pickup_datetime)            as pickup_hour,
        extract(dayofweek from pickup_datetime)        as pickup_day_of_week,

        -- trip metrics
        passenger_count,
        trip_distance_miles,
        timestamp_diff(dropoff_datetime, pickup_datetime, minute) as trip_duration_minutes,

        -- financials
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        congestion_surcharge,
        airport_fee,
        total_amount,
        store_and_fwd_flag

    from all_trips
)

select * from enriched
