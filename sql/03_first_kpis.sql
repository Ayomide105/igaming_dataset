-- 03_first_kpis.sql  |  SYNTHETIC iGaming data  |  First business questions answered in SQL
-- Numbers in the EXPECT lines are from my generator run; yours should match closely.

-- Q1: Monthly GGR (is the business growing?)
SELECT FORMAT(bet_datetime, 'yyyy-MM') AS month,
       ROUND(SUM(stake), 0)  AS stakes,
       ROUND(SUM(payout), 0) AS payouts,
       ROUND(SUM(stake) - SUM(payout), 0) AS ggr
FROM bets
GROUP BY FORMAT(bet_datetime, 'yyyy-MM')
ORDER BY month;

-- Q2: Which channel converts best?  EXPECT ftd_rate_pct about: paid_search 51 | organic 43 | affiliate 34 | social 27
SELECT p.channel,
       COUNT(*) AS players,
       SUM(CASE WHEN f.player_id IS NOT NULL THEN 1 ELSE 0 END) AS depositors,
       ROUND(100.0 * SUM(CASE WHEN f.player_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS ftd_rate_pct
FROM players p
LEFT JOIN (SELECT DISTINCT player_id FROM deposits) f ON f.player_id = p.player_id
GROUP BY p.channel
ORDER BY ftd_rate_pct DESC;

-- Q3: Do welcome-bonus players fade faster?  EXPECT bets_per_depositor about: N 40.6 | Y 16.6
SELECT p.took_welcome_bonus,
       COUNT(DISTINCT p.player_id) AS depositors,
       COUNT(b.bet_id) AS bets,
       ROUND(COUNT(b.bet_id) * 1.0 / COUNT(DISTINCT p.player_id), 1) AS bets_per_depositor
FROM players p
LEFT JOIN bets b ON b.player_id = p.player_id
WHERE p.player_id IN (SELECT player_id FROM deposits)
GROUP BY p.took_welcome_bonus;

-- Q4: How concentrated is revenue?  EXPECT decile 1 about: 67% of stakes, 50% of GGR
WITH per_player AS (
    SELECT player_id, SUM(stake) AS stakes, SUM(stake) - SUM(payout) AS ggr
    FROM bets GROUP BY player_id
), ranked AS (
    SELECT *, NTILE(10) OVER (ORDER BY stakes DESC) AS decile FROM per_player
)
SELECT decile,
       COUNT(*) AS players,
       ROUND(100.0 * SUM(stakes) / SUM(SUM(stakes)) OVER (), 1) AS pct_of_stakes,
       ROUND(100.0 * SUM(ggr)    / SUM(SUM(ggr))    OVER (), 1) AS pct_of_ggr
FROM ranked
GROUP BY decile
ORDER BY decile;

-- Q5: Each player's FIRST deposit (window function ROW_NUMBER)
SELECT player_id, deposit_datetime AS first_deposit_at, amount AS first_deposit_amount
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY deposit_datetime) AS rn FROM deposits) x
WHERE rn = 1
ORDER BY player_id;
