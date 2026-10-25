"""
generate_igaming_data.py  --  SYNTHETIC iGaming player data generator
======================================================================
EVERY ROW THIS SCRIPT CREATES IS ARTIFICIAL. No real player, no real company.

What it builds (3 linked tables, saved as CSV in ../data):
    players   one row per player
    deposits  one row per deposit        (links to players by player_id)
    bets      one row per bet            (links to players by player_id)

How to read this file: go top to bottom. Each STEP says WHAT it does and WHY.
Change numbers in the SETTINGS block, re-run, and watch the printout change.
Run it:   python generate_igaming_data.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

# =====================================================================
# SETTINGS  (the only part you need to edit to experiment)
# =====================================================================
SEED = 42                      # fixes the "randomness" so every run gives identical data
N_PLAYERS = 5000               # how many people register
START = "2025-10-01"           # first possible registration day
END = "2026-09-30"             # last day of the data (12 months)
CURRENCY = "EUR"

# Fictional mixes. Each set of weights must add up to 1.0 (= 100%).
COUNTRIES = {"Germany": .25, "United Kingdom": .25, "Sweden": .15,
             "Canada": .15, "Malta": .10, "Ireland": .10}
CHANNELS = {"affiliate": .35, "organic": .30, "paid_search": .20, "social": .15}
DEVICES = {"mobile": .65, "desktop": .30, "tablet": .05}
METHODS = {"card": .45, "e_wallet": .30, "bank_transfer": .15, "instant_banking": .10}

# PLANTED PATTERN 1: chance a registered player ever makes a deposit, by channel.
DEPOSIT_RATE = {"affiliate": .35, "organic": .45, "paid_search": .50, "social": .30}
# PLANTED PATTERN 2: affiliates bring more bonus-takers.
BONUS_RATE = {"affiliate": .75, "organic": .50, "paid_search": .50, "social": .50}
# PLANTED PATTERN 3: bonus-takers lose interest fast. Number = days for activity to fade.
FADE_DAYS_BONUS, FADE_DAYS_NO_BONUS = 15, 45
HEAVY_FADE_MULT = 2.0          # the top 10% most active players stay twice as long

CASINO_RTP, SPORTS_RTP = 0.95, 0.93        # RTP = share of stakes paid back to players
CASINO_WIN_PROB, SPORTS_WIN_PROB = 0.40, 0.46
EXTRA_DEPOSIT_RATIO = 0.12     # later deposits happen at 12% of the betting rate
STAKE_BASE = 6.0               # average 'typical bet size' per player (EUR)
FIRST_DEPOSIT_AVG, TOPUP_AVG = 25, 20   # average deposit sizes (EUR)
# REALISM RULE: total stakes must be well ABOVE total deposits, because players re-bet their winnings.

# Evening-heavy hours (0-23). Bigger number = busier hour. PLANTED PATTERN 4.
HOUR_WEIGHTS = np.array([3, 2, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4, 5, 5, 6, 8, 10, 11, 11, 9, 6], float)
HOUR_P = HOUR_WEIGHTS / HOUR_WEIGHTS.sum()

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================================
# STEP 0: tools
# =====================================================================
# default_rng(SEED) is our random-number machine. Same SEED -> same numbers every run.
rng = np.random.default_rng(SEED)
START64 = np.datetime64(START, "ns")
END64 = np.datetime64(END, "ns")
N_DAYS = int((END64 - START64) / np.timedelta64(1, "D")) + 1   # 365


def pick(options: dict, size: int):
    """Choose from a {value: weight} dict. 'Weighted choice': not every option is equally likely."""
    return rng.choice(list(options.keys()), size=size, p=list(options.values()))


def random_times(n: int):
    """A random time-of-day for n events, using the evening-heavy HOUR_P weights."""
    hours = rng.choice(24, size=n, p=HOUR_P)
    seconds = rng.integers(0, 3600, size=n)
    return (hours * 3600 + seconds).astype("timedelta64[s]")


def lognormal_with_mean(mean, sigma, size=None):
    """
    A 'lognormal' number is always positive with a long right tail: many small values,
    a few huge ones. That is how real money amounts look. This helper lets us choose
    the AVERAGE directly (the -sigma^2/2 term is the maths that makes the average land on 'mean').
    """
    mu = np.log(mean) - np.asarray(sigma) ** 2 / 2
    return rng.lognormal(mu, sigma, size)


print("STEP 0: random machine ready, seed =", SEED)

# =====================================================================
# STEP 1: PLAYERS  -- who registers, when, from where
# =====================================================================
reg_offsets = rng.integers(0, N_DAYS, N_PLAYERS)                 # a random day number 0..364 for each player
registration = START64 + reg_offsets.astype("timedelta64[D]")    # start date + that many days

players = pd.DataFrame({
    "player_id": np.arange(1, N_PLAYERS + 1),    # 1, 2, 3 ... : the unique ID (primary key)
    "registration_date": registration,
    "country": pick(COUNTRIES, N_PLAYERS),
    "channel": pick(CHANNELS, N_PLAYERS),
    "device": pick(DEVICES, N_PLAYERS),
})
print(f"STEP 1: created {len(players):,} players")

# =====================================================================
# STEP 2: WHO DEPOSITS?  Most registrants never pay anything. That is realistic.
# =====================================================================
p_deposit = players["channel"].map(DEPOSIT_RATE).to_numpy()
is_depositor = rng.random(N_PLAYERS) < p_deposit      # True/False per player; True with probability p_deposit
p_bonus = players["channel"].map(BONUS_RATE).to_numpy()
took_bonus = is_depositor & (rng.random(N_PLAYERS) < p_bonus)    # only depositors can take the welcome bonus
players["took_welcome_bonus"] = np.where(took_bonus, "Y", "N")

dep_idx = np.where(is_depositor)[0]    # positions of depositors in the players table
n_dep = len(dep_idx)
print(f"STEP 2: {n_dep:,} of {N_PLAYERS:,} players deposit  ->  FTD rate (first-time-deposit rate) = {n_dep / N_PLAYERS:.1%}")

# =====================================================================
# STEP 3: FIRST DEPOSIT TIMING  -- 60% deposit on day of registration, the rest within 3 days
# =====================================================================
lag_days = rng.choice([0, 1, 2, 3], size=n_dep, p=[.60, .20, .12, .08])
first_dep_day = registration[dep_idx] + lag_days.astype("timedelta64[D]")
first_dep_day = np.minimum(first_dep_day, END64)                 # cannot go past the end of the data
first_dep_dt = first_dep_day + random_times(n_dep)               # day + time-of-day
print("STEP 3: first-deposit date and time set")

# =====================================================================
# STEP 4: PLAYER 'PERSONALITY'  -- each depositor gets their own habits
# =====================================================================
# Bets per week: lognormal -> most players bet a little, a few bet A LOT ("long tail").
bets_per_week = np.minimum(lognormal_with_mean(5.0, 1.2, n_dep), 200)
rate_per_day = bets_per_week / 7
heavy = bets_per_week >= np.quantile(bets_per_week, 0.90)        # the top 10% by activity
fade_days = np.where(took_bonus[dep_idx], FADE_DAYS_BONUS, FADE_DAYS_NO_BONUS) * np.where(heavy, HEAVY_FADE_MULT, 1.0)
stake_median = lognormal_with_mean(STAKE_BASE, 0.7, n_dep)      # typical bet size for this person
casino_pref = rng.choice([0.9, 0.1], size=n_dep, p=[.6, .4])     # 60% mostly casino, 40% mostly sports
print("STEP 4: each depositor now has a betting rate, a fade speed, a bet size and a product preference")

# =====================================================================
# STEP 5: DAY-BY-DAY ACTIVITY GRID  (rows = players, columns = days since first deposit)
# =====================================================================
# Expected bets on day d =  rate * exp(-d / fade_days)   -> activity DECAYS (retention curve)
#                           * 1.25 on weekends             -> PLANTED PATTERN 5
# Expected extra deposits = small share of that, x1.5 around payday (day 25-3 of month) -> PATTERN 6
d = np.arange(N_DAYS)
dates = first_dep_day[:, None] + d[None, :].astype("timedelta64[D]")   # the calendar date of every cell
in_window = dates <= END64                                             # ignore days after the data ends
days_since_epoch = dates.astype("datetime64[D]").astype("int64")
weekday = (days_since_epoch + 3) % 7                                   # Mon=0 ... Sun=6 (1970-01-01 was a Thursday)
day_of_month = (dates.astype("datetime64[D]") - dates.astype("datetime64[M]")).astype("int64") + 1

decay = np.exp(-d[None, :] / fade_days[:, None])
weekend_boost = np.where(weekday >= 5, 1.25, 1.0)
payday_boost = np.where((day_of_month >= 25) | (day_of_month <= 3), 1.5, 1.0)

lam_bets = rate_per_day[:, None] * decay * weekend_boost * in_window
lam_deps = EXTRA_DEPOSIT_RATIO * rate_per_day[:, None] * decay * payday_boost * in_window
lam_deps[:, 0] = 0                                  # no extra deposit on day 0 (the first deposit already covers it)

# Poisson = the standard "random count of events" distribution. Input: expected count. Output: actual count.
bet_counts = rng.poisson(lam_bets)
dep_counts = rng.poisson(lam_deps)
print(f"STEP 5: activity grid built -> {bet_counts.sum():,} bets and {dep_counts.sum():,} extra deposits will be created")


def expand(counts):
    """Turn a grid of counts into one row per event: (player position, day number)."""
    p, day = np.nonzero(counts)
    reps = counts[p, day]
    return np.repeat(p, reps), np.repeat(day, reps)


# =====================================================================
# STEP 6: BETS  -- one row per bet
# =====================================================================
bp, bd = expand(bet_counts)
n_bets = len(bp)
bet_dt = first_dep_day[bp] + bd.astype("timedelta64[D]") + random_times(n_bets)

# A player cannot bet BEFORE their first deposit. Fix the rare day-0 rows that landed earlier.
too_early = bet_dt < first_dep_dt[bp]
bet_dt[too_early] = first_dep_dt[bp][too_early] + rng.integers(60, 3600, too_early.sum()).astype("timedelta64[s]")
bet_dt = np.minimum(bet_dt, END64 + np.timedelta64(86399, "s"))

is_casino = rng.random(n_bets) < casino_pref[bp]
stake = stake_median[bp] * rng.lognormal(0, 0.5, n_bets) * np.where(is_casino, 1.0, 3.0)   # sports stakes are bigger
stake = np.maximum(np.round(stake, 2), 0.10)

# PAYOUT: this is where the HOUSE EDGE lives.
# A bet wins with probability win_prob. If it wins, it pays stake * multiplier, where the AVERAGE multiplier
# is set so that  win_prob * avg_multiplier = RTP.   Example: casino 0.40 * 2.375 = 0.95 -> 95% returned on average.
win_prob = np.where(is_casino, CASINO_WIN_PROB, SPORTS_WIN_PROB)
rtp = np.where(is_casino, CASINO_RTP, SPORTS_RTP)
spread = np.where(is_casino, 1.0, 0.4)               # casino wins vary a lot (jackpots); sports less so
multiplier = lognormal_with_mean(rtp / win_prob, spread)
won = rng.random(n_bets) < win_prob
payout = np.round(np.where(won, stake * multiplier, 0.0), 2)

bets = pd.DataFrame({
    "player_id": dep_idx[bp] + 1,                    # +1 because player_id starts at 1, positions start at 0
    "bet_datetime": bet_dt,
    "product": np.where(is_casino, "casino", "sportsbook"),
    "stake": stake,
    "payout": payout,
}).sort_values("bet_datetime", kind="stable").reset_index(drop=True)
bets.insert(0, "bet_id", np.arange(1, len(bets) + 1))
print(f"STEP 6: {len(bets):,} bets created")

# =====================================================================
# STEP 7: DEPOSITS  -- first deposit for every depositor + later top-ups
# =====================================================================
money_scale = np.sqrt(stake_median / STAKE_BASE)     # bigger bettors deposit bigger amounts


def to_amount(x):
    return np.clip(np.round(x), 10, 2000)            # whole euros, between 10 and 2,000


first_dep = pd.DataFrame({
    "player_id": dep_idx + 1,
    "deposit_datetime": first_dep_dt,
    "amount": to_amount(lognormal_with_mean(FIRST_DEPOSIT_AVG, 0.8, n_dep) * money_scale),
})
dp, dd = expand(dep_counts)
extra_dt = first_dep_day[dp] + dd.astype("timedelta64[D]") + random_times(len(dp))
extra_dep = pd.DataFrame({
    "player_id": dep_idx[dp] + 1,
    "deposit_datetime": extra_dt,
    "amount": to_amount(lognormal_with_mean(TOPUP_AVG, 0.8, len(dp)) * money_scale[dp]),
})
deposits = pd.concat([first_dep, extra_dep], ignore_index=True)
deposits["method"] = pick(METHODS, len(deposits))
deposits = deposits.sort_values("deposit_datetime", kind="stable").reset_index(drop=True)
deposits.insert(0, "deposit_id", np.arange(1, len(deposits) + 1))
print(f"STEP 7: {len(deposits):,} deposits created ({n_dep:,} first deposits + {len(extra_dep):,} later ones)")

# =====================================================================
# STEP 8: VALIDATION  -- never trust data you have not tested
# =====================================================================
reg_by_id = players.set_index("player_id")["registration_date"]
first_dep_by_id = deposits.groupby("player_id")["deposit_datetime"].min()

dep_before_reg = int((deposits["deposit_datetime"] < deposits["player_id"].map(reg_by_id)).sum())
bet_before_reg = int((bets["bet_datetime"] < bets["player_id"].map(reg_by_id)).sum())
bet_before_first_dep = int((bets["bet_datetime"] < bets["player_id"].map(first_dep_by_id)).sum())
orphans = int((~deposits["player_id"].isin(players["player_id"])).sum() + (~bets["player_id"].isin(players["player_id"])).sum())
bets_no_deposit = int(bets["player_id"].map(first_dep_by_id).isna().sum())

stakes_total, payouts_total = bets["stake"].sum(), bets["payout"].sum()
ggr = stakes_total - payouts_total                    # GGR (gross gaming revenue) = stakes - payouts
per_player = bets.groupby("player_id").agg(stakes=("stake", "sum"), payouts=("payout", "sum"))
per_player["ggr"] = per_player["stakes"] - per_player["payouts"]
top_n = max(1, int(len(per_player) * 0.10))
top = per_player.sort_values("stakes", ascending=False).head(top_n)
top10_stake_share = top["stakes"].sum() / per_player["stakes"].sum()
top10_ggr_share = top["ggr"].sum() / per_player["ggr"].sum()

turnover_multiple = stakes_total / deposits["amount"].sum()   # stakes per 1 EUR deposited; should be well above 1
print("\n--- VALIDATION (the first four must be 0) ---")
print("deposits before registration:", dep_before_reg)
print("bets before registration    :", bet_before_reg)
print("bets before first deposit   :", bet_before_first_dep)
print("orphan player_ids           :", orphans)
print(f"total stakes {stakes_total:,.0f} | payouts {payouts_total:,.0f} | GGR {ggr:,.0f} | RTP {payouts_total / stakes_total:.1%}")
print(f"total deposits {deposits['amount'].sum():,.0f} | turnover multiple (stakes / deposits) {turnover_multiple:.1f}x")
print(f"top 10% of betting players: {top10_stake_share:.0%} of stakes, {top10_ggr_share:.0%} of GGR")

print("\n--- DID THE PLANTED PATTERNS APPEAR? ---")
dep_rate = players.assign(dep=is_depositor).groupby("channel")["dep"].mean().round(3)
print("deposit rate by channel :", dep_rate.to_dict())
bonus_flag = players.set_index("player_id")["took_welcome_bonus"]
bets_by_bonus = bets.groupby(bets["player_id"].map(bonus_flag)).size() / players[is_depositor].groupby("took_welcome_bonus").size()
print("avg bets per depositor, by bonus (Y/N):", bets_by_bonus.round(1).to_dict())
evening = bets["bet_datetime"].dt.hour.between(18, 23).mean()
print(f"share of bets placed 18:00-23:59: {evening:.0%}")

# =====================================================================
# STEP 9: SAVE  -- CSVs are what you import into SQL
# =====================================================================
players_out = players.copy()
players_out["registration_date"] = players_out["registration_date"].dt.strftime("%Y-%m-%d")
players_out.to_csv(OUT_DIR / "players.csv", index=False)
deposits.to_csv(OUT_DIR / "deposits.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
bets.to_csv(OUT_DIR / "bets.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

checks = {
    "n_players": int(N_PLAYERS), "n_depositors": int(n_dep), "ftd_rate": float(n_dep / N_PLAYERS),
    "dep_before_reg": dep_before_reg, "bet_before_reg": bet_before_reg,
    "bet_before_first_dep": bet_before_first_dep, "orphans": orphans, "bets_no_deposit": bets_no_deposit,
    "top10_stake_share": float(top10_stake_share), "top10_ggr_share": float(top10_ggr_share),
    "evening_share": float(evening), "turnover_multiple": float(turnover_multiple), "currency": CURRENCY, "seed": SEED, "start": START, "end": END,
}
(OUT_DIR / "checks.json").write_text(json.dumps(checks, indent=2))
print(f"\nSTEP 9: saved players.csv, deposits.csv, bets.csv to {OUT_DIR}")
