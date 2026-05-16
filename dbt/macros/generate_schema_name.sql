{% macro generate_schema_name(custom_schema_name, node) -%}
    {#
      Override dbt's default schema naming so that:
        - staging models  → nyc_taxi_staging  (not <default_schema>_staging)
        - marts models    → nyc_taxi_marts
      This keeps BigQuery dataset names clean and consistent regardless of
      the profile's default dataset value.
    #}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
