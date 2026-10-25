# PROJECT GUIDE: Synthetic iGaming Player Data
Everything you need to finish this project WITHOUT any AI help. Keep this file in your repo.

---
## 0. If a usage limit hits
1. Keep working from this guide. Every remaining step is below with exact commands.
2. To continue with Claude later, open a new chat, attach this file and say:
   "Continue my synthetic iGaming SQL project from Phase __ step __. Here is my last result: [paste or screenshot]."

## 1. Status
| Phase | What | Status |
|---|---|---|
| 1 | Blueprint: 3 tables (players, deposits, bets) | DONE |
| 2 | Generate players | DONE (Python script) |
| 3 | Generate deposits and bets | DONE (Python script) |
| 4 | Load into SQL Server and validate | IN PROGRESS: load script was running; checks not yet run |
| 5 | Package: README, screenshots, GitHub | README drafted; screenshots and push still to do |

## 2. What each file does
| File | Purpose |
|---|---|
| python/generate_igaming_data.py | Creates the 3 CSVs. Read it top to bottom; every STEP is commented. |
| python/build_workbook.py | Packs the CSVs into one Excel workbook with a Checks sheet. |
| python/build_sql_loader.py | Turns the CSVs into the single SQL loading script. |
| sql/01_create_and_load.sql | Creates 3 tables and loads all 66,564 rows. |
| sql/02_validation_checks.sql | Proves the data is sane (expected answers inside). |
| sql/03_first_kpis.sql | First business questions: GGR, FTD by channel, bonus effect, concentration. |
| README.md | The business-case write-up (executive-readable). |

To rebuild everything: open a terminal in the `python` folder and run, in order:
`python generate_igaming_data.py`, `python build_workbook.py`, `python build_sql_loader.py`
(needs `pip install pandas numpy openpyxl`). Same seed = identical data.

---
## 3. PHASE 4: Load and validate (about 45 min)

**4.1 Confirm the load finished (5 min)**
- In SSMS, check the dropdown shows `iGamingDB`.
- When the tab title no longer says "Executing...", look at the Results tab: three rows, 5000 / 8766 / 52798.
- Finish line: those 3 numbers match.
- If the tab shows red errors, go to section 6.

**4.2 Run the validation checks (15 min)**
- File > Open > File > `02_validation_checks.sql`. Press Execute. Several result grids appear.
- Compare each grid to its EXPECT comment:
  - Check 1 counts: 5000 / 8766 / 52798
  - Check 2: all four results = 0
  - Check 3: stakes about 646,709; payouts about 608,883; GGR about 37,826; RTP about 0.9415
  - Check 4: deposits 184,938
  - Check 5: depositors 1968, players 5000, FTD 39.4
- Finish line: all match. Tiny differences in Check 3 mean the data was regenerated; that is fine if the rules in Check 2 still show 0.

**4.3 Run the first KPI queries (15 min)**
- Open `03_first_kpis.sql`. Select one query at a time (highlight it) and press Execute.
- Q2 should show paid_search highest and social lowest. Q3 should show bonus "Y" far below "N".
- Finish line: you can say in one sentence what each result means.

**4.4 Take screenshots (10 min)**
- Screenshot the Check 1 and Check 2 results. Save as `docs/sql_checks.png`.
- Screenshot Q2, Q4 and Q3 results as charts if you can: in SSMS copy the grid into Excel, insert a bar chart, save as `docs/chart1.png`, `chart2.png`, `chart3.png` (FTD by channel, share by decile, bets per depositor by bonus).

---
## 4. PHASE 5: Package (about 90 min)

**5.1 Data dictionary (5 min)**: already inside `igaming_synthetic_data.xlsx`, sheet "Data Dictionary". Nothing to write.

**5.2 README (30 min)**
- Open README.md. Read sections 1, 2, 4, 5 aloud. If a non-technical person could not repeat them, simplify.
- Check the numbers in section 4 against your SQL results from 4.2/4.3 and fix any that differ.
- Keep the word SYNTHETIC visible. Do not claim real-world findings: the patterns were planted.
- Finish line: every placeholder image in README exists in /docs.

**5.3 One-page PDF (optional, 15 min)**: copy README sections 1 to 6 into Word, export as PDF, save as `docs/one_page_summary.pdf`.

**5.4 Push to GitHub (15 min)**
Copy the whole project folder into your repo folder, then in a terminal:
```
cd C:\path\to\your-repo
git status
git add .
git commit -m "Add synthetic iGaming dataset, SQL loader and validation checks"
git push
```
- If the push is rejected: `git pull --rebase`, then `git push` again.
- Never commit passwords or connection strings. Open the repo page in a browser and confirm the README renders.

**5.5 LinkedIn post (optional, 20 min)**
Template: "I built a synthetic iGaming player database (5,000 players, 52,798 bets) to practise retention and bonus analysis safely. Top 10% of bettors place 67% of stakes. Full business case and SQL on GitHub: [link]. All data is synthetic."

---
## 5. After the project is done (this week)
1. Finish course module #6 (joins) if you haven't.
2. Build the KPI dashboard in Power BI from these tables: GGR by month, FTD rate by channel, active players.
3. Next project: cohort retention (D1/D7/D30), split by bonus vs no bonus. Search: "cohort retention analysis SQL".

## 6. Troubleshooting
| Problem | Cause | Fix |
|---|---|---|
| "Incorrect syntax near ','" | You ran a CSV as if it were SQL | Never paste CSV into a query window; use 01_create_and_load.sql |
| "Invalid object name 'players'" | Wrong database selected | Pick iGamingDB in the dropdown, run again |
| Still "Executing..." after 3+ min | Express edition is slow on large scripts | Wait; check Messages tab for "(1000 rows affected)" lines |
| Foreign key error during load | Tables created in wrong order | Re-run the whole 01 script; it drops and rebuilds in the right order |
| Counts are lower than 5000/8766/52798 | Script stopped midway | Re-run the whole 01 script |
| "No module named pandas" | Library missing | `pip install pandas numpy openpyxl` |
| Push rejected by GitHub | Remote has newer commits | `git pull --rebase`, then `git push` |

## 7. Definition of done
- [ ] 3 tables loaded; counts 5000 / 8766 / 52798
- [ ] 02 checks all match; Check 2 all zeros
- [ ] 03 queries run; you can explain each result in one sentence
- [ ] Screenshots saved in /docs
- [ ] README numbers verified, SYNTHETIC visible
- [ ] Pushed to GitHub and README renders

## 8. If someone asks you to explain it (30 seconds)
"I built a realistic but fake customer database for an online casino and sportsbook: most sign-ups never deposit, a few players generate most of the revenue, bonus players leave fast, and the house wins about 5%. I loaded it into SQL Server, proved it has no impossible data, and used it to answer first business questions. Everything is labelled synthetic."
