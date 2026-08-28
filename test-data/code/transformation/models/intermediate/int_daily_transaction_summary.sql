{{
    config(
        materialized='ephemeral',
        tags=['intermediate', 'transactions', 'daily']
    )
}}

/*
    Intermediate model: Daily Transaction Summary
    Purpose: Aggregate transactions to daily level per account.
    Used by mart_transaction_analytics and mart_customer_360.
    Grain: one row per (account_id, transaction_date)
*/

with transactions as (

    select * from {{ ref('stg_transactions') }}

),

-- daily aggregation per account
daily_agg as (

    select
        account_id,
        transaction_date,

        -- volume metrics
        count(*) as total_transaction_count,
        count(case when transaction_type = 'credit' then 1 end) as credit_count,
        count(case when transaction_type = 'debit' then 1 end) as debit_count,
        count(case when transaction_type = 'transfer' then 1 end) as transfer_count,
        count(case when transaction_type = 'fee' then 1 end) as fee_count,

        -- amount metrics (signed)
        sum(signed_amount) as net_amount,
        sum(case when signed_amount > 0 then signed_amount else 0 end) as total_credits,
        sum(case when signed_amount < 0 then abs(signed_amount) else 0 end) as total_debits,

        -- absolute amounts
        sum(transaction_amount) as gross_transaction_volume,
        avg(transaction_amount) as avg_transaction_amount,
        max(transaction_amount) as max_transaction_amount,
        min(transaction_amount) as min_transaction_amount,
        percentile_approx(transaction_amount, 0.5) as median_transaction_amount,

        -- fees
        sum(fee_amount) as total_fees,

        -- fx metrics
        count(case when transaction_currency != settlement_currency then 1 end) as fx_transaction_count,
        sum(
            case
                when transaction_currency != settlement_currency
                then transaction_amount
                else 0
            end
        ) as fx_transaction_volume,

        -- channel breakdown
        count(case when transaction_channel = 'online' then 1 end) as online_count,
        count(case when transaction_channel = 'branch' then 1 end) as branch_count,
        count(case when transaction_channel = 'atm' then 1 end) as atm_count,
        count(case when transaction_channel = 'mobile' then 1 end) as mobile_count,
        count(case when transaction_channel = 'pos' then 1 end) as pos_count,
        count(case when transaction_channel = 'swift' then 1 end) as swift_count,

        -- risk indicators
        count(case when is_suspicious = true then 1 end) as suspicious_transaction_count,
        count(case when is_pep_related = true then 1 end) as pep_related_count,
        sum(
            case when is_suspicious = true then transaction_amount else 0 end
        ) as suspicious_transaction_volume,
        max(risk_score) as max_daily_risk_score,
        avg(risk_score) as avg_daily_risk_score,

        -- counterparty diversity
        count(distinct counterparty_bank_code) as unique_counterparty_banks,
        count(distinct counterparty_country) as unique_counterparty_countries,

        -- cross-border indicators
        count(
            case when counterparty_country is not null
                  and counterparty_country != '' then 1 end
        ) as cross_border_transaction_count,

        -- time-of-day patterns (for fraud detection)
        count(
            case
                when hour(transaction_datetime) between 0 and 5 then 1
            end
        ) as overnight_transaction_count,

        -- settlement metrics
        count(
            case when transaction_status = 'settled' then 1 end
        ) as settled_count,
        count(
            case when transaction_status = 'pending' then 1 end
        ) as pending_count,
        count(
            case when transaction_status = 'failed' then 1 end
        ) as failed_count,

        -- partition key passthrough
        transaction_date as partition_date

    from transactions
    group by account_id, transaction_date

),

-- add running totals and period comparisons
enriched as (

    select
        {{ dbt_utils.generate_surrogate_key(['account_id', 'transaction_date']) }} as daily_summary_sk,

        account_id,
        transaction_date,
        partition_date,

        -- volume
        total_transaction_count,
        credit_count,
        debit_count,
        transfer_count,
        fee_count,

        -- amounts
        net_amount,
        total_credits,
        total_debits,
        gross_transaction_volume,
        avg_transaction_amount,
        max_transaction_amount,
        min_transaction_amount,
        median_transaction_amount,
        total_fees,

        -- fx
        fx_transaction_count,
        fx_transaction_volume,

        -- channels
        online_count,
        branch_count,
        atm_count,
        mobile_count,
        pos_count,
        swift_count,

        -- risk
        suspicious_transaction_count,
        pep_related_count,
        suspicious_transaction_volume,
        max_daily_risk_score,
        avg_daily_risk_score,

        -- counterparty
        unique_counterparty_banks,
        unique_counterparty_countries,
        cross_border_transaction_count,
        overnight_transaction_count,

        -- settlement
        settled_count,
        pending_count,
        failed_count,

        -- derived ratios
        case
            when total_transaction_count > 0
            then round(failed_count / total_transaction_count, 4)
            else 0
        end as failure_rate,

        case
            when total_transaction_count > 0
            then round(suspicious_transaction_count / total_transaction_count, 4)
            else 0
        end as suspicious_rate,

        -- 7-day rolling volume (window function)
        sum(gross_transaction_volume) over (
            partition by account_id
            order by transaction_date
            rows between 6 preceding and current row
        ) as rolling_7d_volume,

        sum(total_transaction_count) over (
            partition by account_id
            order by transaction_date
            rows between 6 preceding and current row
        ) as rolling_7d_count,

        -- metadata
        current_timestamp() as _computed_at

    from daily_agg

)

select * from enriched
