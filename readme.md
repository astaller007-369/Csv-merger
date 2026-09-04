# CSV Merge Ledger

A small Streamlit app that compares two CSV files, matches rows by **team + date**,
and fills empty cells in one file using values from the other — without ever
overwriting a cell that already has data.

## What it does

1. Upload **File A** (the sheet you want updated) and **File B** (the sheet you're copying from).
2. Pick the team and date column in each file — these are the match keys.
3. Optionally filter everything down to a single team.
4. Choose one or more column pairs to copy between (File A column ← File B column).
5. Run the fill: for every row where team + date match in both files, any **empty**
   File A cell in a mapped column gets filled from File B. Cells that already have
   data are left untouched.
6. Review the highlighted results and download the updated CSV.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py