"""
build_sql_loader.py -- turns the 3 CSVs into ONE SQL Server script:
    drop old tables -> create players/deposits/bets (with keys) -> insert all rows -> count check.
Why batches of 1,000? SQL Server allows at most 1,000 rows in one INSERT ... VALUES statement.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
players = pd.read_csv(ROOT / "data" / "players.csv")
deposits = pd.read_csv(ROOT / "data" / "deposits.csv")
bets = pd.read_csv(ROOT / "data" / "bets.csv")

def q(s):                       # text value -> 'text' (doubling any apostrophe is the SQL escape rule)
    return "'" + str(s).replace("'", "''") + "'"

def inserts(table, cols, rows):
    out = []
    for i in range(0, len(rows), 1000):
        chunk = rows[i:i + 1000]
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n" + ",\n".join(chunk) + ";\nGO\n")
    return out

p_rows = [f"({r.player_id},{q(r.registration_date)},{q(r.country)},{q(r.channel)},{q(r.device)},{q(r.took_welcome_bonus)})"
          for r in players.itertuples()]
d_rows = [f"({r.deposit_id},{r.player_id},{q(r.deposit_datetime)},{r.amount:.2f},{q(r.method)})" for r in deposits.itertuples()]
b_rows = [f"({r.bet_id},{r.player_id},{q(r.bet_datetime)},{q(r.product)},{r.stake:.2f},{r.payout:.2f})" for r in bets.itertuples()]

head = """-- SYNTHETIC iGaming data: players, deposits, bets. ALL DATA IS ARTIFICIAL.
-- HOW TO RUN: 1) pick your database in the dropdown at the top of SSMS  2) press Execute (F5).
-- Safe to re-run: it drops and rebuilds the three tables each time.

DROP TABLE IF EXISTS bets;
DROP TABLE IF EXISTS deposits;
DROP TABLE IF EXISTS players;
GO

CREATE TABLE players (
    player_id          INT          NOT NULL PRIMARY KEY,
    registration_date  DATE         NOT NULL,
    country            NVARCHAR(50) NOT NULL,
    channel            NVARCHAR(50) NOT NULL,
    device             NVARCHAR(50) NOT NULL,
    took_welcome_bonus CHAR(1)      NOT NULL
);
CREATE TABLE deposits (
    deposit_id       INT           NOT NULL PRIMARY KEY,
    player_id        INT           NOT NULL REFERENCES players(player_id),
    deposit_datetime DATETIME2(0)  NOT NULL,
    amount           DECIMAL(10,2) NOT NULL,
    method           NVARCHAR(30)  NOT NULL
);
CREATE TABLE bets (
    bet_id       INT           NOT NULL PRIMARY KEY,
    player_id    INT           NOT NULL REFERENCES players(player_id),
    bet_datetime DATETIME2(0)  NOT NULL,
    product      NVARCHAR(20)  NOT NULL,
    stake        DECIMAL(10,2) NOT NULL,
    payout       DECIMAL(10,2) NOT NULL
);
GO

"""
tail = """
-- CHECK: expect 5000 / 8766 / 52798
SELECT 'players' AS tbl, COUNT(*) AS n FROM players
UNION ALL SELECT 'deposits', COUNT(*) FROM deposits
UNION ALL SELECT 'bets', COUNT(*) FROM bets;
"""
parts = [head]
parts += inserts("players", ["player_id", "registration_date", "country", "channel", "device", "took_welcome_bonus"], p_rows)
parts += inserts("deposits", ["deposit_id", "player_id", "deposit_datetime", "amount", "method"], d_rows)
parts += inserts("bets", ["bet_id", "player_id", "bet_datetime", "product", "stake", "payout"], b_rows)
parts.append(tail)
out = ROOT / "sql" / "01_create_and_load.sql"
out.write_text("".join(parts), encoding="utf-8")
print("saved", out, f"({out.stat().st_size/1e6:.1f} MB)", "rows:", len(p_rows), len(d_rows), len(b_rows))
