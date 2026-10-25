-- 02_validation_checks.sql  |  SYNTHETIC iGaming data  |  Run AFTER 01_create_and_load.sql
-- Select iGamingDB in the dropdown first. Each query shows what you should see.

-- CHECK 1: row counts.  EXPECT: players 5000 | deposits 8766 | bets 52798
SELECT 'players' AS tbl, COUNT(*) AS n FROM players
UNION ALL SELECT 'deposits', COUNT(*) FROM deposits
UNION ALL SELECT 'bets', COUNT(*) FROM bets;

-- CHECK 2: logic errors.  EXPECT: every result = 0
SELECT 'deposits_before_registration' AS check_name, COUNT(*) AS result
FROM deposits d JOIN players p ON p.player_id = d.player_id
WHERE d.deposit_datetime < CAST(p.registration_date AS DATETIME2(0))
UNION ALL
SELECT 'bets_before_registration', COUNT(*)
FROM bets b JOIN players p ON p.player_id = b.player_id
WHERE b.bet_datetime < CAST(p.registration_date AS DATETIME2(0))
UNION ALL
SELECT 'bets_before_first_deposit', COUNT(*)
FROM bets b
JOIN (SELECT player_id, MIN(deposit_datetime) AS first_dep FROM deposits GROUP BY player_id) f
  ON f.player_id = b.player_id
WHERE b.bet_datetime < f.first_dep
UNION ALL
SELECT 'bets_from_players_who_never_deposited', COUNT(*)
FROM bets b
WHERE NOT EXISTS (SELECT 1 FROM deposits d WHERE d.player_id = b.player_id);

-- CHECK 3: money.  EXPECT (rounded): stakes 646709 | payouts 608883 | ggr 37826 | rtp 0.9415
-- GGR (gross gaming revenue) = stakes - payouts.  RTP (return to player) = payouts / stakes.
SELECT ROUND(SUM(stake), 0)                AS stakes,
       ROUND(SUM(payout), 0)               AS payouts,
       ROUND(SUM(stake) - SUM(payout), 0)  AS ggr,
       ROUND(SUM(payout) / SUM(stake), 4)  AS rtp
FROM bets;

-- CHECK 4: total deposits.  EXPECT 184938.  Stakes must be well above deposits (players re-bet winnings).
SELECT SUM(amount) AS total_deposits FROM deposits;

-- CHECK 5: FTD (first-time-deposit) rate.  EXPECT: depositors 1968 | players 5000 | ftd_rate_pct 39.4
SELECT COUNT(DISTINCT d.player_id) AS depositors,
       COUNT(DISTINCT p.player_id) AS players,
       ROUND(COUNT(DISTINCT d.player_id) * 100.0 / COUNT(DISTINCT p.player_id), 1) AS ftd_rate_pct
FROM players p LEFT JOIN deposits d ON d.player_id = p.player_id;
