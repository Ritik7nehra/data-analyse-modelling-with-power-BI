-- What if discounts were capped? Lines discounted above the cap are re-priced at the cap discount.
--   scenario profit = volume_retention * (gross_sales * (1 - cap) - cost)    (cost scales with volume)
-- volume_retention = 1.0 assumes no demand loss (upper bound); 0.0 = those lines are dropped entirely.
-- This is a what-if estimate, not a forecast: demand response to price is the key unknown.
CREATE OR REPLACE TABLE mart_discount_what_if AS
WITH caps AS (SELECT * FROM (VALUES (0.10), (0.20), (0.30)) AS t(discount_cap)),
retention AS (SELECT * FROM (VALUES (1.00), (0.80), (0.60), (0.40), (0.20), (0.00)) AS t(volume_retention)),
scenarios AS (SELECT * FROM caps CROSS JOIN retention),
totals AS (SELECT SUM(profit) AS total_profit FROM fact_orders)
SELECT
    s.discount_cap,
    s.volume_retention,
    COUNT(*) FILTER (WHERE f.discount > s.discount_cap)                                   AS affected_lines,
    SUM(f.profit) FILTER (WHERE f.discount > s.discount_cap)                              AS baseline_profit_affected,
    SUM(s.volume_retention * (f.gross_sales * (1 - s.discount_cap) - f.cost))
        FILTER (WHERE f.discount > s.discount_cap)                                        AS scenario_profit_affected,
    SUM(s.volume_retention * (f.gross_sales * (1 - s.discount_cap) - f.cost))
        FILTER (WHERE f.discount > s.discount_cap)
      - SUM(f.profit) FILTER (WHERE f.discount > s.discount_cap)                          AS profit_delta,
    (SUM(s.volume_retention * (f.gross_sales * (1 - s.discount_cap) - f.cost))
        FILTER (WHERE f.discount > s.discount_cap)
      - SUM(f.profit) FILTER (WHERE f.discount > s.discount_cap)) / ANY_VALUE(t.total_profit) AS profit_delta_pct_of_total
FROM scenarios s
CROSS JOIN fact_orders f
CROSS JOIN totals t
GROUP BY s.discount_cap, s.volume_retention
ORDER BY s.discount_cap, s.volume_retention DESC;
