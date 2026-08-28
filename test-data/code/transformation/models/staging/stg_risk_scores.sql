{{
    config(
        materialized='view',
        tags=['staging', 'risk', 'daily']
    )
}}

/*
    Staging model: Risk Scores
    Source: Oracle DWH → raw_banking.risk_scores (Iceberg)
    Purpose: Standardize risk assessment records from the credit risk engine.
    Grain: one row per risk_assessment_id (multiple per customer over time)
*/

with source as (

    select * from {{ source('raw_banking', 'risk_scores') }}

),

renamed as (

    select
        -- surrogate key
        {{ dbt_utils.generate_surrogate_key(['risk_assessment_id']) }} as risk_assessment_sk,

        -- natural keys
        risk_assessment_id,
        account_id,

        -- pii: hash customer identifier
        sha2(
            concat(cast(customer_id as string), '{{ var("pii_hash_salt") }}'),
            256
        ) as customer_id_hashed,

        -- risk scores (normalized to 0-1000 scale)
        cast(credit_score as int) as credit_score,
        cast(behavioural_score as decimal(6, 2)) as behavioural_score,
        cast(fraud_probability as decimal(8, 6)) as fraud_probability,
        cast(default_probability as decimal(8, 6)) as default_probability,
        cast(loss_given_default as decimal(8, 6)) as loss_given_default,
        cast(exposure_at_default as decimal(18, 4)) as exposure_at_default,
        cast(expected_loss as decimal(18, 4)) as expected_loss,

        -- risk classification
        lower(trim(risk_rating)) as risk_rating,
        lower(trim(risk_model_version)) as risk_model_version,
        lower(trim(assessment_type)) as assessment_type,
        lower(trim(risk_driver_primary)) as risk_driver_primary,
        lower(trim(risk_driver_secondary)) as risk_driver_secondary,

        -- regulatory risk weights (Basel III/IV)
        cast(risk_weight_standardised as decimal(6, 4)) as risk_weight_standardised,
        cast(risk_weight_irb as decimal(6, 4)) as risk_weight_irb,
        lower(trim(asset_class_regulatory)) as asset_class_regulatory,
        lower(trim(exposure_class)) as exposure_class,

        -- watchlist & alerts
        cast(is_watchlist as boolean) as is_watchlist,
        cast(is_default as boolean) as is_default,
        cast(days_past_due as int) as days_past_due,
        lower(trim(delinquency_bucket)) as delinquency_bucket,

        -- temporal
        cast(assessment_date as date) as assessment_date,
        cast(next_review_date as date) as next_review_date,
        cast(score_valid_until as date) as score_valid_until,

        -- metadata
        cast(_ingested_at as timestamp) as _ingested_at,
        cast(_source_system as string) as _source_system,
        current_timestamp() as _stg_loaded_at

    from source

    where risk_assessment_id is not null
      and assessment_date is not null

)

select * from renamed
