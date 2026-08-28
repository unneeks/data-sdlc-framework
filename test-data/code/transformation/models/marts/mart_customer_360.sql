{{
    config(
        materialized='incremental',
        unique_key='account_id',
        incremental_strategy='merge',
        file_format='iceberg',
        partition_by=[{'field': 'partition_date', 'data_type': 'date', 'granularity': 'month'}],
        table_properties={
            'write.format.default': 'parquet',
            'write.parquet.compression-codec': 'zstd',
            'write.metadata.delete-after-commit.enabled': 'true',
            'write.metadata.previous-versions-max': '5',
            'write.distribution-mode': 'hash'
        },
        tags=['marts', 'customer', 'daily', 'regulatory']
    )
}}

/*
    Mart: Customer 360
    Purpose: Complete customer view combining account details, risk profile,
    and transaction behaviour. Primary consumption layer for BI, CRM,
    and regulatory reporting.
    Grain: one row per account_id
    Refresh: incremental merge on account_id
    Consumers: Tableau (BI), Salesforce (CRM), Regulatory team
*/

with customer_enriched as (

    select * from {{ ref('int_customer_enriched') }}

),

transaction_summary as (

    select * from {{ ref('int_daily_transaction_summary') }}

),

-- aggregate transaction history per account (last 90 days focus)
account_transaction_profile as (

    select
        account_id,

        -- lifetime metrics
        min(transaction_date) as first_transaction_date,
        max(transaction_date) as last_transaction_date_derived,
        count(distinct transaction_date) as active_days_count,
        sum(total_transaction_count) as lifetime_transaction_count,
        sum(gross_transaction_volume) as lifetime_gross_volume,
        sum(net_amount) as lifetime_net_flow,

        -- last 30 days
        sum(
            case when transaction_date >= date_add(current_date(), -30)
            then total_transaction_count else 0 end
        ) as txn_count_30d,
        sum(
            case when transaction_date >= date_add(current_date(), -30)
            then gross_transaction_volume else 0 end
        ) as volume_30d,
        sum(
            case when transaction_date >= date_add(current_date(), -30)
            then total_credits else 0 end
        ) as credits_30d,
        sum(
            case when transaction_date >= date_add(current_date(), -30)
            then total_debits else 0 end
        ) as debits_30d,

        -- last 90 days
        sum(
            case when transaction_date >= date_add(current_date(), -90)
            then total_transaction_count else 0 end
        ) as txn_count_90d,
        sum(
            case when transaction_date >= date_add(current_date(), -90)
            then gross_transaction_volume else 0 end
        ) as volume_90d,

        -- risk indicators (last 90 days)
        sum(
            case when transaction_date >= date_add(current_date(), -90)
            then suspicious_transaction_count else 0 end
        ) as suspicious_count_90d,
        sum(
            case when transaction_date >= date_add(current_date(), -90)
            then cross_border_transaction_count else 0 end
        ) as cross_border_count_90d,
        max(
            case when transaction_date >= date_add(current_date(), -90)
            then max_daily_risk_score else null end
        ) as max_risk_score_90d,

        -- channel preferences (last 90 days)
        sum(
            case when transaction_date >= date_add(current_date(), -90)
            then mobile_count else 0 end
        ) as mobile_txn_90d,
        sum(
            case when transaction_date >= date_add(current_date(), -90)
            then online_count else 0 end
        ) as online_txn_90d,
        sum(
            case when transaction_date >= date_add(current_date(), -90)
            then branch_count else 0 end
        ) as branch_txn_90d,

        -- fee revenue
        sum(total_fees) as lifetime_fees_paid,
        sum(
            case when transaction_date >= date_add(current_date(), -365)
            then total_fees else 0 end
        ) as fees_paid_12m,

        -- fx activity
        sum(fx_transaction_count) as lifetime_fx_count,
        sum(fx_transaction_volume) as lifetime_fx_volume

    from transaction_summary
    group by account_id

),

-- determine preferred channel
channel_preference as (

    select
        account_id,
        case
            when mobile_txn_90d >= online_txn_90d
                 and mobile_txn_90d >= branch_txn_90d then 'mobile'
            when online_txn_90d >= branch_txn_90d then 'online'
            else 'branch'
        end as preferred_channel

    from account_transaction_profile

),

-- final assembly
final as (

    select
        -- keys
        c.account_sk,
        c.account_id,
        c.customer_id_hashed,

        -- account profile
        c.account_type,
        c.account_status,
        c.currency_code,
        c.branch_code,
        c.country_code,
        c.customer_segment,
        c.regulatory_jurisdiction,
        c.relationship_manager_id,
        c.is_joint_account,

        -- balances
        c.current_balance,
        c.credit_limit,
        c.available_balance,
        c.credit_utilization_ratio,

        -- tenure & activity
        c.account_opened_date,
        c.account_tenure_years,
        c.activity_status,
        c.days_since_last_transaction,

        -- risk profile
        c.credit_score,
        c.behavioural_score,
        c.fraud_probability,
        c.default_probability,
        c.expected_loss,
        c.risk_rating,
        c.composite_risk_tier,
        c.is_watchlist,
        c.is_default,
        c.days_past_due,
        c.delinquency_bucket,
        c.latest_risk_assessment_date,

        -- regulatory
        c.kyc_verified,
        c.kyc_status_derived,
        c.kyc_expiry_date,
        c.aml_flagged,
        c.fatca_reportable,
        c.risk_weight_standardised,
        c.risk_weight_irb,
        c.asset_class_regulatory,
        c.exposure_class,
        c.exposure_at_default,
        c.loss_given_default,

        -- transaction behaviour
        t.lifetime_transaction_count,
        t.lifetime_gross_volume,
        t.lifetime_net_flow,
        t.txn_count_30d,
        t.volume_30d,
        t.credits_30d,
        t.debits_30d,
        t.txn_count_90d,
        t.volume_90d,
        t.suspicious_count_90d,
        t.cross_border_count_90d,
        t.max_risk_score_90d,

        -- channel & engagement
        ch.preferred_channel,
        t.mobile_txn_90d,
        t.online_txn_90d,
        t.branch_txn_90d,

        -- revenue
        t.lifetime_fees_paid,
        t.fees_paid_12m,
        t.lifetime_fx_count,
        t.lifetime_fx_volume,

        -- derived segmentation scores
        case
            when t.volume_90d > 1000000 then 'platinum'
            when t.volume_90d > 500000 then 'gold'
            when t.volume_90d > 100000 then 'silver'
            else 'standard'
        end as value_tier,

        case
            when c.is_default = true then 'collections'
            when c.days_past_due > 90 then 'pre_collections'
            when c.composite_risk_tier = 'high_risk' then 'watch'
            when c.activity_status = 'dormant' then 'reactivation'
            when t.txn_count_30d = 0 and c.account_status = 'active' then 'engagement'
            else 'nurture'
        end as next_best_action_segment,

        -- partition
        current_date() as partition_date,

        -- metadata
        current_timestamp() as _mart_loaded_at,
        '{{ invocation_id }}' as _dbt_invocation_id

    from customer_enriched c
    left join account_transaction_profile t
        on c.account_id = t.account_id
    left join channel_preference ch
        on t.account_id = ch.account_id

    {% if is_incremental() %}
    where c._stg_loaded_at > (select max(_mart_loaded_at) from {{ this }})
       or c.latest_risk_assessment_date > (
           select max(latest_risk_assessment_date) from {{ this }} where account_id = c.account_id
       )
    {% endif %}

)

select * from final
