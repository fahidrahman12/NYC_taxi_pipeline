-- Payment type dimension sourced from the seed file so it is self-contained
-- and does not depend on raw trip data containing every code.

select
    {{ dbt_utils.generate_surrogate_key(['payment_type_id']) }} as payment_type_key,
    payment_type_id,
    payment_type_description
from {{ ref('payment_types') }}
