-- Seven-day service spend, change, and rank using CTEs and window functions.
WITH daily_service AS (
  SELECT usage_date, service, SUM(amount) AS daily_cost
  FROM costs
  GROUP BY usage_date, service
), rolling AS (
  SELECT usage_date, service, daily_cost,
    AVG(daily_cost) OVER (
      PARTITION BY service ORDER BY usage_date
      ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS prior_7_day_average
  FROM daily_service
), latest AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY service ORDER BY usage_date DESC) AS recency
  FROM rolling
)
SELECT usage_date, service, ROUND(daily_cost, 2) AS daily_cost,
  ROUND(prior_7_day_average, 2) AS prior_7_day_average,
  ROUND(100 * (daily_cost - prior_7_day_average) / NULLIF(prior_7_day_average, 0), 1) AS change_pct,
  RANK() OVER (ORDER BY daily_cost DESC) AS cost_rank
FROM latest
WHERE recency = 1
ORDER BY cost_rank;

