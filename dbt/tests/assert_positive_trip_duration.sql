-- Fails if any trip has a zero or negative duration after staging validation.
-- This guards against pickup/dropoff timestamps being swapped or identical.

select *
from {{ ref('fact_trips') }}
where trip_duration_minutes <= 0
