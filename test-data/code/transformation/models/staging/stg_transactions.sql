{{
    config(
        materialized='view',
        tags=['staging', 'transactions', 'daily']
    )
}}

/*
    Staging model: Transactions
    Source: Oracle DWH → raw_banking.transactions (Iceberg)
    Purpose: Clean and standardize transaction records with proper typing.
    Grain: one row per transaction_id
    Volume: ~50M rows/day in production
*/

with source as (

    select * from {{ source('raw_banking', 'transactions') }}

),

renamed as (

    select
        -- surrogate key
        {{ dbt_utils.generate_surrogate_key(['transaction_id']) }} as transaction_sk,

        -- natural keys
        transaction_id,
        account_id,

        -- pii: hash counterparty identifiers
        sha2(
            concat(cast(counterparty_account_id as string), '{{ var("pii_hash_salt") }}'),
            256
        ) as counterparty_account_id_hashed,

        -- transaction classification
        lower(trim(transaction_type)) as transaction_type,
        lower(trim(transaction_channel)) as transaction_channel,
        lower(trim(transaction_status)) as transaction_status,
        lower(trim(payment_method)) as payment_method,
        lower(trim(transaction_category)) as transaction_category,

        -- amounts
        cast(transaction_amount as decimal(18, 4)) as transaction_amount,
        cast(
            case
                when lower(trim(transaction_type)) in ('debit', 'withdrawal', 'fee', 'charge')
                    then -1 * abs(transaction_amount)
                else abs(transaction_amount)
            end as decimal(18, 4)
        ) as signed_amount,
        upper(trim(transaction_currency)) as transaction_currency,
        cast(exchange_rate as decimal(12, 6)) as exchange_rate,
        cast(settlement_amount as decimal(18, 4)) as settlement_amount,
        upper(trim(settlement_currency)) as settlement_currency,

        -- fees
        cast(coalesce(fee_amount, 0) as decimal(18, 4)) as fee_amount,
        lower(trim(fee_type)) as fee_type,

        -- counterparty
        upper(trim(counterparty_bank_code)) as counterparty_bank_code,
        upper(trim(counterparty_country)) as counterparty_country,

        -- risk & compliance
        cast(risk_score as decimal(5, 2)) as risk_score,
        cast(is_suspicious as boolean) as is_suspicious,
        cast(is_pep_related as boolean) as is_pep_related,
        lower(trim(sanctions_check_status)) as sanctions_check_status,
        lower(trim(aml_alert_level)) as aml_alert_level,

        -- reference
        trim(reference_number) as reference_number,
        trim(merchant_category_code) as merchant_category_code,
        trim(swift_message_type) as swift_message_type,

        -- timestamps
        cast(transaction_datetime as timestamp) as transaction_datetime,
        cast(transaction_datetime as date) as transaction_date,
        cast(value_date as date) as value_date,
        cast(settlement_date as date) as settlement_date,
        cast(posted_datetime as timestamp) as posted_datetime,

        -- partition key
        cast(transaction_datetime as date) as partition_date,

        -- metadata
        cast(_ingested_at as timestamp) as _ingested_at,
        cast(_source_system as string) as _source_system,
        cast(_batch_id as string) as _batch_id,
        current_timestamp() as _stg_loaded_at

    from source

    where transaction_id is not null
      and transaction_status != 'voided'
      and transaction_datetime is not null

)

select * from renamed
