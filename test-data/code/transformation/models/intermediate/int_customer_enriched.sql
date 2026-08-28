{{
    config(
        materialized='ephemeral',
        tags=['intermediate', 'customer', 'daily']
    )
}}

/*
    Intermediate model: Customer Enriched
    Purpose: Joins customer accounts with their latest risk assessment to produce
    a single enriched customer record for downstream marts.
    Grain: one row per account_id (latest risk score per account)
*/

with customers as (

    select * from {{ ref('stg_customer_accounts') }}

),

risk_scores as (

    select * from {{ ref('stg_risk_scores') }}

),

-- get the most recent risk assessment per account using row_number
latest_risk as (

    select
        account_id,
        customer_id_hashed,
        credit_score,
        behavioural_score,
        fraud_probability,
        default_probability,
        loss_given_default,
        exposure_at_default,
        expected_loss,
        risk_rating,
        risk_model_version,
        risk_driver_primary,
        risk_driver_secondary,
        risk_weight_standardised,
        risk_weight_irb,
        asset_class_regulatory,
        exposure_class,
        is_watchlist,
        is_default,
        days_past_due,
        delinquency_bucket,
        assessment_date as latest_risk_assessment_date,
        next_review_date as risk_next_review_date,
        row_number() over (
            partition by account_id
            order by assessment_date desc, _ingested_at desc
        ) as rn

    from risk_scores

),

latest_risk_filtered as (

    select * from latest_risk
    where rn = 1

),

-- derive customer tenure and activity indicators
customer_derived as (

    select
        *,

        -- tenure calculation
        datediff(current_date(), account_opened_date) as account_tenure_days,
        floor(datediff(current_date(), account_opened_date) / 365.25) as account_tenure_years,

        -- activity indicators
        datediff(current_date(), last_transaction_date) as days_since_last_transaction,
        case
            when datediff(current_date(), last_transaction_date) <= 30 then 'active'
            when datediff(current_date(), last_transaction_date) <= 90 then 'low_activity'
            when datediff(current_date(), last_transaction_date) <= 365 then 'inactive'
            else 'dormant'
        end as activity_status,

        -- balance utilization (for credit products)
        case
            when credit_limit > 0
                then round(current_balance / credit_limit, 4)
            else null
        end as credit_utilization_ratio,

        -- kyc status
        case
            when kyc_verified = true and kyc_expiry_date > current_date() then 'valid'
            when kyc_verified = true and kyc_expiry_date <= current_date() then 'expired'
            when kyc_verified = false then 'pending'
            else 'unknown'
        end as kyc_status_derived

    from customers

),

-- final join: customer + latest risk
enriched as (

    select
        c.account_sk,
        c.account_id,
        c.customer_id_hashed,
        c.account_type,
        c.account_status,
        c.currency_code,
        c.branch_code,
        c.country_code,
        c.opening_balance,
        c.current_balance,
        c.credit_limit,
        c.available_balance,
        c.customer_segment,
        c.risk_category,
        c.relationship_manager_id,
        c.is_joint_account,
        c.is_dormant,
        c.kyc_verified,
        c.aml_flagged,
        c.fatca_reportable,
        c.regulatory_jurisdiction,
        c.account_opened_date,
        c.last_transaction_date,
        c.kyc_expiry_date,
        c.next_review_date,

        -- derived fields
        c.account_tenure_days,
        c.account_tenure_years,
        c.days_since_last_transaction,
        c.activity_status,
        c.credit_utilization_ratio,
        c.kyc_status_derived,

        -- risk fields from latest assessment
        r.credit_score,
        r.behavioural_score,
        r.fraud_probability,
        r.default_probability,
        r.loss_given_default,
        r.exposure_at_default,
        r.expected_loss,
        r.risk_rating,
        r.risk_model_version,
        r.risk_driver_primary,
        r.risk_driver_secondary,
        r.risk_weight_standardised,
        r.risk_weight_irb,
        r.asset_class_regulatory,
        r.exposure_class,
        r.is_watchlist,
        r.is_default,
        r.days_past_due,
        r.delinquency_bucket,
        r.latest_risk_assessment_date,
        r.risk_next_review_date,

        -- composite risk indicator
        case
            when r.is_default = true then 'default'
            when r.is_watchlist = true then 'watchlist'
            when r.credit_score < 500 then 'high_risk'
            when r.credit_score < 650 then 'medium_risk'
            when r.credit_score >= 650 then 'low_risk'
            else 'unscored'
        end as composite_risk_tier,

        -- metadata
        c._stg_loaded_at

    from customer_derived c
    left join latest_risk_filtered r
        on c.account_id = r.account_id

)

select * from enriched
