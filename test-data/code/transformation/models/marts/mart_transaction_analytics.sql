{{
    config(
        materialized='incremental',
        unique_key='daily_summary_sk',
        incremental_strategy='merge',
        file_format='iceberg',
        partition_by=[{'field': 'transaction_date', 'data_type': 'date', 'granularity': 'day'}],
        table_properties={
            'write.format.default': 'parquet',
            'write.parquet.compression-codec': 'zstd',
            'write.target-file-size-bytes': '536870912',
            'write.metadata.delete-after-commit.enabled': 'true',
            'write.metadata.previous-versions-max': '3'
        },
        tags=['marts', 'transactions', 'daily', 'analytics'],
        post_hook=[
            "alter table {{ this }} set tblproperties ('gc.enabled' = 'true')"
        ]
    )
}}

/*
    Mart: Transaction Analytics
    Purpose: Daily transaction aggregates enriched with customer context
    for analytics, fraud detection, and AML monitoring.
    Grain: one row per (account_id, transaction_date)
    Refresh: incremental on transaction_date
    Consumers: Analytics team, Fraud detection, AML monitoring
*/

with daily_summary as (

    select * from {{ ref('int_daily_transaction_summary') }}

    {% if is_incremental() %}
    where transaction_date > (select max(transaction_date) from {{ this }})
    {% endif %}

),

customer_context as (

    select
        account_id,
        customer_id_hashed,
        account_type,
        account_status,
        currency_code,
        country_code,
        customer_segment,
        risk_category,
        credit_score,
        composite_risk_tier,
        regulatory_jurisdiction,
        aml_flagged,
        is_watchlist,
        account_tenure_years
    from {{ ref('int_customer_enriched') }}

),

-- calculate anomaly indicators using statistical thresholds
account_baselines as (

    select
        account_id,
        avg(gross_transaction_volume) as baseline_daily_volume,
        stddev(gross_transaction_volume) as stddev_daily_volume,
        avg(total_transaction_count) as baseline_daily_count,
        stddev(total_transaction_count) as stddev_daily_count,
        avg(max_daily_risk_score) as baseline_risk_score
    from daily_summary
    group by account_id

),

-- assemble the analytics mart
final as (

    select
        -- keys
        ds.daily_summary_sk,
        ds.account_id,
        cust.customer_id_hashed,

        -- date dimensions
        ds.transaction_date,
        year(ds.transaction_date) as transaction_year,
        month(ds.transaction_date) as transaction_month,
        dayofweek(ds.transaction_date) as day_of_week,
        case
            when dayofweek(ds.transaction_date) in (1, 7) then true
            else false
        end as is_weekend,
        quarter(ds.transaction_date) as transaction_quarter,
        weekofyear(ds.transaction_date) as week_of_year,

        -- customer context
        cust.account_type,
        cust.account_status,
        cust.currency_code,
        cust.country_code,
        cust.customer_segment,
        cust.risk_category,
        cust.credit_score,
        cust.composite_risk_tier,
        cust.regulatory_jurisdiction,
        cust.aml_flagged as customer_aml_flagged,
        cust.is_watchlist as customer_on_watchlist,
        cust.account_tenure_years,

        -- volume metrics
        ds.total_transaction_count,
        ds.credit_count,
        ds.debit_count,
        ds.transfer_count,
        ds.fee_count,

        -- amount metrics
        ds.net_amount,
        ds.total_credits,
        ds.total_debits,
        ds.gross_transaction_volume,
        ds.avg_transaction_amount,
        ds.max_transaction_amount,
        ds.min_transaction_amount,
        ds.median_transaction_amount,
        ds.total_fees,

        -- fx
        ds.fx_transaction_count,
        ds.fx_transaction_volume,

        -- channels
        ds.online_count,
        ds.branch_count,
        ds.atm_count,
        ds.mobile_count,
        ds.pos_count,
        ds.swift_count,

        -- risk & compliance
        ds.suspicious_transaction_count,
        ds.pep_related_count,
        ds.suspicious_transaction_volume,
        ds.max_daily_risk_score,
        ds.avg_daily_risk_score,
        ds.failure_rate,
        ds.suspicious_rate,

        -- counterparty
        ds.unique_counterparty_banks,
        ds.unique_counterparty_countries,
        ds.cross_border_transaction_count,
        ds.overnight_transaction_count,

        -- settlement
        ds.settled_count,
        ds.pending_count,
        ds.failed_count,

        -- rolling metrics
        ds.rolling_7d_volume,
        ds.rolling_7d_count,

        -- anomaly detection flags
        case
            when bl.stddev_daily_volume > 0
                 and ds.gross_transaction_volume > (bl.baseline_daily_volume + 3 * bl.stddev_daily_volume)
            then true
            else false
        end as is_volume_anomaly,

        case
            when bl.stddev_daily_count > 0
                 and ds.total_transaction_count > (bl.baseline_daily_count + 3 * bl.stddev_daily_count)
            then true
            else false
        end as is_count_anomaly,

        case
            when ds.overnight_transaction_count > 5
                 and ds.max_daily_risk_score > 0.7
            then true
            else false
        end as is_overnight_risk_flag,

        case
            when ds.cross_border_transaction_count > 10
                 and ds.unique_counterparty_countries > 5
                 and cust.composite_risk_tier in ('high_risk', 'watchlist')
            then true
            else false
        end as is_cross_border_risk_flag,

        -- composite daily risk score (0-100)
        round(
            (coalesce(ds.suspicious_rate, 0) * 30) +
            (case when ds.overnight_transaction_count > 3 then 15 else 0 end) +
            (case when ds.cross_border_transaction_count > 5 then 20 else 0 end) +
            (coalesce(ds.max_daily_risk_score, 0) * 20) +
            (case when ds.failure_rate > 0.1 then 15 else 0 end),
            2
        ) as composite_daily_risk_score,

        -- regulatory flags
        case
            when ds.gross_transaction_volume > 10000
                 and ds.unique_counterparty_countries > 2
            then true
            else false
        end as ctr_reportable,

        case
            when ds.suspicious_transaction_count > 0
                 or (ds.gross_transaction_volume > 50000 and ds.overnight_transaction_count > 3)
            then true
            else false
        end as sar_candidate,

        -- partition
        ds.transaction_date as partition_date,

        -- metadata
        current_timestamp() as _mart_loaded_at,
        '{{ invocation_id }}' as _dbt_invocation_id

    from daily_summary ds
    left join customer_context cust
        on ds.account_id = cust.account_id
    left join account_baselines bl
        on ds.account_id = bl.account_id

)

select * from final
