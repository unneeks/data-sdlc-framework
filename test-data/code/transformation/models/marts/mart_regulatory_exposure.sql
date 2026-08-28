{{
    config(
        materialized='table',
        file_format='iceberg',
        partition_by=[{'field': 'reporting_date', 'data_type': 'date', 'granularity': 'month'}],
        table_properties={
            'write.format.default': 'parquet',
            'write.parquet.compression-codec': 'zstd'
        },
        tags=['marts', 'regulatory', 'daily', 'basel']
    )
}}

/*
    Mart: Regulatory Exposure Report
    Purpose: Basel III/IV regulatory capital and exposure report.
    Aggregates risk-weighted assets (RWA), expected credit loss (ECL),
    and regulatory exposure metrics for capital adequacy reporting.
    Grain: one row per (account_id, reporting_date)
    Materialization: full table rebuild (regulatory accuracy requires no incremental drift)
    Consumers: Risk management, Regulatory reporting (COREP), Finance
*/

with customer_risk as (

    select * from {{ ref('int_customer_enriched') }}
    where account_status in ('active', 'dormant', 'suspended', 'frozen')

),

transactions_recent as (

    select
        account_id,
        sum(gross_transaction_volume) as volume_90d,
        sum(cross_border_transaction_count) as cross_border_count_90d,
        sum(suspicious_transaction_count) as suspicious_count_90d,
        max(max_daily_risk_score) as peak_risk_score_90d
    from {{ ref('int_daily_transaction_summary') }}
    where transaction_date >= date_add(current_date(), -90)
    group by account_id

),

-- calculate risk-weighted assets per Basel III standardised approach
rwa_calculation as (

    select
        cr.account_id,
        cr.customer_id_hashed,
        cr.account_type,
        cr.currency_code,
        cr.country_code,
        cr.regulatory_jurisdiction,
        cr.customer_segment,
        cr.credit_score,
        cr.risk_rating,
        cr.composite_risk_tier,
        cr.asset_class_regulatory,
        cr.exposure_class,

        -- exposure amounts
        cr.current_balance,
        cr.credit_limit,
        coalesce(cr.exposure_at_default, cr.current_balance) as ead,

        -- risk weights
        cr.risk_weight_standardised,
        cr.risk_weight_irb,

        -- rwa calculation (standardised)
        round(
            coalesce(cr.exposure_at_default, cr.current_balance)
            * coalesce(cr.risk_weight_standardised, 1.0),
            4
        ) as rwa_standardised,

        -- rwa calculation (irb)
        round(
            coalesce(cr.exposure_at_default, cr.current_balance)
            * coalesce(cr.risk_weight_irb, cr.risk_weight_standardised, 1.0),
            4
        ) as rwa_irb,

        -- expected credit loss (ecl) components
        cr.default_probability as pd,
        cr.loss_given_default as lgd,
        coalesce(cr.exposure_at_default, cr.current_balance) as exposure,

        -- ecl stage classification (ifrs 9)
        case
            when cr.is_default = true then 3
            when cr.days_past_due > 30
                 or cr.is_watchlist = true
                 or cr.credit_score < 500
            then 2
            else 1
        end as ifrs9_stage,

        -- 12-month ecl (stage 1)
        case
            when cr.is_default = false and cr.days_past_due <= 30 and coalesce(cr.is_watchlist, false) = false
            then round(
                coalesce(cr.default_probability, 0.01)
                * coalesce(cr.loss_given_default, 0.45)
                * coalesce(cr.exposure_at_default, cr.current_balance),
                4
            )
            else 0
        end as ecl_12_month,

        -- lifetime ecl (stage 2 & 3)
        case
            when cr.is_default = true
                 or cr.days_past_due > 30
                 or cr.is_watchlist = true
                 or cr.credit_score < 500
            then round(
                coalesce(cr.default_probability, 0.05)
                * coalesce(cr.loss_given_default, 0.45)
                * coalesce(cr.exposure_at_default, cr.current_balance)
                * (cr.account_tenure_years + 1),  -- rough lifetime multiplier
                4
            )
            else 0
        end as ecl_lifetime,

        -- delinquency and default
        cr.is_default,
        cr.is_watchlist,
        cr.days_past_due,
        cr.delinquency_bucket,

        -- compliance flags
        cr.kyc_verified,
        cr.kyc_status_derived,
        cr.aml_flagged,
        cr.fatca_reportable,

        -- activity context
        tr.volume_90d,
        tr.cross_border_count_90d,
        tr.suspicious_count_90d,
        tr.peak_risk_score_90d

    from customer_risk cr
    left join transactions_recent tr
        on cr.account_id = tr.account_id

),

-- regulatory concentration limits
concentration_metrics as (

    select
        country_code,
        regulatory_jurisdiction,
        asset_class_regulatory,
        count(*) as exposure_count,
        sum(ead) as total_exposure,
        sum(rwa_standardised) as total_rwa_std,
        avg(coalesce(pd, 0)) as avg_pd
    from rwa_calculation
    group by country_code, regulatory_jurisdiction, asset_class_regulatory

),

-- final assembly with all regulatory metrics
final as (

    select
        -- keys
        {{ dbt_utils.generate_surrogate_key(['r.account_id', 'current_date()']) }} as exposure_sk,
        r.account_id,
        r.customer_id_hashed,

        -- reporting date
        current_date() as reporting_date,

        -- exposure classification
        r.account_type,
        r.currency_code,
        r.country_code,
        r.regulatory_jurisdiction,
        r.customer_segment,
        r.asset_class_regulatory,
        r.exposure_class,
        r.composite_risk_tier,
        r.risk_rating,

        -- exposure amounts
        r.current_balance,
        r.credit_limit,
        r.ead as exposure_at_default,

        -- risk-weighted assets
        r.risk_weight_standardised,
        r.risk_weight_irb,
        r.rwa_standardised,
        r.rwa_irb,

        -- expected credit loss (ifrs 9)
        r.ifrs9_stage,
        r.pd as probability_of_default,
        r.lgd as loss_given_default,
        r.ecl_12_month,
        r.ecl_lifetime,
        case
            when r.ifrs9_stage = 1 then r.ecl_12_month
            else r.ecl_lifetime
        end as ecl_provision,

        -- credit quality
        r.credit_score,
        r.is_default,
        r.is_watchlist,
        r.days_past_due,
        r.delinquency_bucket,

        -- compliance & kyc
        r.kyc_verified,
        r.kyc_status_derived,
        r.aml_flagged,
        r.fatca_reportable,

        -- activity risk indicators
        r.volume_90d as transaction_volume_90d,
        r.cross_border_count_90d,
        r.suspicious_count_90d,
        r.peak_risk_score_90d,

        -- concentration context (% of total in same jurisdiction/asset class)
        round(
            r.ead / nullif(c.total_exposure, 0),
            6
        ) as concentration_pct_jurisdiction,

        -- large exposure flag (>10% of capital proxy)
        case
            when r.ead > 1000000 then true
            else false
        end as is_large_exposure,

        -- regulatory reporting flags
        case
            when r.aml_flagged = true
                 or r.suspicious_count_90d > 0
            then true
            else false
        end as requires_sar_review,

        case
            when r.kyc_status_derived = 'expired'
                 or r.kyc_verified = false
            then true
            else false
        end as kyc_remediation_required,

        case
            when r.ifrs9_stage >= 2
                 and r.days_past_due > 60
            then true
            else false
        end as requires_impairment_review,

        -- capital buffer indicators
        case
            when r.composite_risk_tier = 'high_risk' then 0.025  -- countercyclical buffer
            when r.composite_risk_tier = 'watchlist' then 0.015
            else 0.0
        end as countercyclical_buffer_addon,

        -- partition
        current_date() as partition_date,

        -- metadata
        current_timestamp() as _mart_loaded_at,
        '{{ invocation_id }}' as _dbt_invocation_id

    from rwa_calculation r
    left join concentration_metrics c
        on r.country_code = c.country_code
        and r.regulatory_jurisdiction = c.regulatory_jurisdiction
        and r.asset_class_regulatory = c.asset_class_regulatory

)

select * from final
