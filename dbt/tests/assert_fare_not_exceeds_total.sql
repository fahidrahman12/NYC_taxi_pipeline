-- The base fare should never exceed the total amount charged.
-- A violation indicates corrupted financial data in the source.

select *
from {{ ref('fact_trips') }}
where fare_amount > total_amount
