{{
    config(
        materialized='view',
        tags=['staging', 'customer', 'daily']
    )
}}

/*
    Staging model: Customer Accounts
    Source: Oracle DWH → raw_banking.customer_accounts (Iceberg)
    Purpose: Clean, type-cast, and standardize customer account records.
    PII handling: customer_id is hashed for downstream consumption.
    Grain: one row per account_id
*/

with source as (

    select * from {{ source('raw_banking', 'customer_accounts') }}

),

renamed as (

    select
        -- surrogate key
        {{ dbt_utils.generate_surrogate_key(['account_id']) }} as account_sk,

        -- natural keys
        account_id,

        -- pii: hash customer identifiers for downstream models
        sha2(
            concat(cast(customer_id as string), '{{ var("pii_hash_salt") }}'),
            256
        ) as customer_id_hashed,

        -- account attributes
        lower(trim(account_type)) as account_type,
        lower(trim(account_status)) as account_status,
        upper(trim(currency_code)) as currency_code,
        upper(trim(branch_code)) as branch_code,
        upper(trim(country_code)) as country_code,

        -- financial
        cast(opening_balance as decimal(18, 4)) as opening_balance,
        cast(current_balance as decimal(18, 4)) as current_balance,
        cast(credit_limit as decimal(18, 4)) as credit_limit,
        cast(available_balance as decimal(18, 4)) as available_balance,

        -- classification
        lower(trim(customer_segment)) as customer_segment,
        lower(trim(risk_category)) as risk_category,
        cast(relationship_manager_id as string) as relationship_manager_id,
        cast(is_joint_account as boolean) as is_joint_account,
        cast(is_dormant as boolean) as is_dormant,

        -- regulatory
        cast(kyc_verified as boolean) as kyc_verified,
        cast(aml_flagged as boolean) as aml_flagged,
        cast(fatca_reportable as boolean) as fatca_reportable,
        lower(trim(regulatory_jurisdiction)) as regulatory_jurisdiction,

        -- dates
        cast(account_opened_date as date) as account_opened_date,
        cast(last_transaction_date as timestamp) as last_transaction_date,
        cast(kyc_expiry_date as date) as kyc_expiry_date,
        cast(next_review_date as date) as next_review_date,

        -- metadata
        cast(_ingested_at as timestamp) as _ingested_at,
        cast(_source_system as string) as _source_system,
        current_timestamp() as _stg_loaded_at

    from source

    where account_id is not null
      and account_status != 'deleted'

)

select * from renamed
