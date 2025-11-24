/*
================================================================================
CASH FLOW AFFORDABILITY (CFA) - SNOWFLAKE QUERY
================================================================================
Calcula CFA para todos los usuarios activos usando nuevos umbrales:
- Tier 3: CFA >= 70%
- Tier 2: CFA 60-69%
- Tier 1: CFA 50-59%
- Denied: CFA < 50%

Metodología:
1. can_pay[d] = 1 if daily_balance >= biweekly_parcel else 0
2. pct_90 = sum(can_pay last 90 days) / 90
3. pct_6m = sum(can_pay 6 months) / total_days
4. CFA = (pct_90 × 0.70) + (pct_6m × 0.30)
================================================================================
*/

-- ============================================================================
-- PASO 1: Definir biweekly parcels por tier (basado en estructura de préstamos)
-- ============================================================================
WITH tier_parcels AS (
    SELECT 1 AS tier_num, 51.98 AS biweekly_parcel  -- Tier 1: $100, 30 días, 2 pagos
    UNION ALL
    SELECT 2 AS tier_num, 39.72 AS biweekly_parcel  -- Tier 2: $150, 60 días, 4 pagos
    UNION ALL
    SELECT 3 AS tier_num, 35.80 AS biweekly_parcel  -- Tier 3: $200, 90 días, 6 pagos
),

-- ============================================================================
-- PASO 2: Obtener usuarios activos (con transacciones últimos 90 días + 7+ días activos)
-- ============================================================================
active_users AS (
    SELECT
        user_id,
        COUNT(DISTINCT DATE_TRUNC('day', transaction_date)) AS active_days,
        MAX(transaction_date) AS last_transaction_date
    FROM user_transactions  -- 👈 CAMBIAR POR TU TABLA
    WHERE transaction_date >= DATEADD(month, -6, CURRENT_DATE())
    GROUP BY user_id
    HAVING
        MAX(transaction_date) >= DATEADD(day, -90, CURRENT_DATE())
        AND COUNT(DISTINCT DATE_TRUNC('day', transaction_date)) >= 7
),

-- ============================================================================
-- PASO 3: Calcular daily_balance, daily_income, daily_expenses por usuario/día
-- ============================================================================
daily_balances AS (
    SELECT
        t.user_id,
        DATE_TRUNC('day', t.transaction_date) AS transaction_date,

        -- Balance al final del día
        SUM(t.balance) AS daily_balance,  -- 👈 AJUSTAR según tu columna de balance

        -- Income del día (transacciones positivas)
        SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS daily_income,

        -- Expenses del día (transacciones negativas)
        ABS(SUM(CASE WHEN t.amount < 0 THEN t.amount ELSE 0 END)) AS daily_expenses

    FROM user_transactions t  -- 👈 CAMBIAR POR TU TABLA
    INNER JOIN active_users au ON t.user_id = au.user_id
    WHERE t.transaction_date >= DATEADD(month, -6, CURRENT_DATE())
    GROUP BY
        t.user_id,
        DATE_TRUNC('day', t.transaction_date)
),

-- ============================================================================
-- PASO 4: Calcular can_pay para cada día usando cada biweekly_parcel
-- ============================================================================
can_pay_daily AS (
    SELECT
        db.user_id,
        db.transaction_date,
        db.daily_balance,
        db.daily_income,
        db.daily_expenses,
        tp.tier_num,
        tp.biweekly_parcel,

        -- can_pay = 1 si balance >= parcel, 0 si no
        CASE
            WHEN db.daily_balance >= tp.biweekly_parcel THEN 1
            ELSE 0
        END AS can_pay,

        -- Marcar si es últimos 90 días
        CASE
            WHEN db.transaction_date >= DATEADD(day, -90, CURRENT_DATE()) THEN 1
            ELSE 0
        END AS is_last_90_days

    FROM daily_balances db
    CROSS JOIN tier_parcels tp  -- Evaluar cada usuario contra cada tier
),

-- ============================================================================
-- PASO 5: Calcular pct_90, pct_6m, y CFA final por usuario y tier
-- ============================================================================
cfa_by_user_tier AS (
    SELECT
        user_id,
        tier_num,
        biweekly_parcel,

        -- Total días analizados (6 meses)
        COUNT(*) AS total_days_6m,

        -- Días en últimos 90 días
        SUM(is_last_90_days) AS days_in_90,

        -- Can pay últimos 90 días
        SUM(CASE WHEN is_last_90_days = 1 THEN can_pay ELSE 0 END) AS can_pay_90d,

        -- Can pay 6 meses
        SUM(can_pay) AS can_pay_6m,

        -- pct_90 = can_pay_90d / 90
        SUM(CASE WHEN is_last_90_days = 1 THEN can_pay ELSE 0 END) / 90.0 AS pct_90,

        -- pct_6m = can_pay_6m / total_days
        SUM(can_pay) / COUNT(*)::FLOAT AS pct_6m,

        -- CFA = (pct_90 × 0.70) + (pct_6m × 0.30)
        (SUM(CASE WHEN is_last_90_days = 1 THEN can_pay ELSE 0 END) / 90.0 * 0.70) +
        (SUM(can_pay) / COUNT(*)::FLOAT * 0.30) AS cfa_score,

        -- Avg balance, income
        AVG(daily_balance) AS avg_balance,
        AVG(daily_income) AS avg_daily_income

    FROM can_pay_daily
    GROUP BY
        user_id,
        tier_num,
        biweekly_parcel
),

-- ============================================================================
-- PASO 6: Asignar MEJOR tier posible para cada usuario (tier más alto que califica)
-- ============================================================================
user_best_tier AS (
    SELECT
        user_id,

        -- Determinar el tier más alto que califica con nuevos umbrales
        CASE
            WHEN MAX(CASE WHEN tier_num = 3 AND cfa_score >= 0.70 THEN 1 ELSE 0 END) = 1 THEN 3
            WHEN MAX(CASE WHEN tier_num = 2 AND cfa_score >= 0.60 THEN 1 ELSE 0 END) = 1 THEN 2
            WHEN MAX(CASE WHEN tier_num = 1 AND cfa_score >= 0.50 THEN 1 ELSE 0 END) = 1 THEN 1
            ELSE 0  -- Denied
        END AS assigned_tier,

        -- CFA score del tier asignado
        MAX(CASE
            WHEN tier_num = 3 AND cfa_score >= 0.70 THEN cfa_score
            WHEN tier_num = 2 AND cfa_score >= 0.60 THEN cfa_score
            WHEN tier_num = 1 AND cfa_score >= 0.50 THEN cfa_score
            ELSE NULL
        END) AS cfa_score,

        -- Avg monthly income (aproximado: avg_daily_income * 30)
        MAX(avg_daily_income) * 30 AS avg_monthly_income,

        -- Avg balance
        MAX(avg_balance) AS avg_balance

    FROM cfa_by_user_tier
    GROUP BY user_id
)

-- ============================================================================
-- RESULTADO FINAL: Resumen por Tier
-- ============================================================================
SELECT
    CASE
        WHEN assigned_tier = 3 THEN 'Tier 3'
        WHEN assigned_tier = 2 THEN 'Tier 2'
        WHEN assigned_tier = 1 THEN 'Tier 1'
        ELSE 'Denied'
    END AS tier,

    -- Conteo de usuarios
    COUNT(*) AS user_count,

    -- % del total
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_total,

    -- Avg CFA score
    ROUND(AVG(cfa_score), 4) AS avg_cfa_score,

    -- Loan capacity (loan amount * user count)
    CASE
        WHEN assigned_tier = 3 THEN COUNT(*) * 200
        WHEN assigned_tier = 2 THEN COUNT(*) * 150
        WHEN assigned_tier = 1 THEN COUNT(*) * 100
        ELSE 0
    END AS loan_capacity,

    -- Avg monthly income
    ROUND(AVG(avg_monthly_income), 0) AS avg_monthly_income,

    -- Avg balance
    ROUND(AVG(avg_balance), 2) AS avg_balance

FROM user_best_tier
GROUP BY assigned_tier
ORDER BY assigned_tier DESC;


-- ============================================================================
-- QUERY ADICIONAL: Detalle por usuario (para validación)
-- ============================================================================
/*
SELECT
    user_id,
    CASE
        WHEN assigned_tier = 3 THEN 'Tier 3'
        WHEN assigned_tier = 2 THEN 'Tier 2'
        WHEN assigned_tier = 1 THEN 'Tier 1'
        ELSE 'Denied'
    END AS tier,
    ROUND(cfa_score, 4) AS cfa_score,
    ROUND(avg_monthly_income, 0) AS avg_monthly_income,
    ROUND(avg_balance, 2) AS avg_balance
FROM user_best_tier
ORDER BY assigned_tier DESC, cfa_score DESC
LIMIT 100;
*/
