name: Sarkar Automation Engine
on:
  push:
    paths:
      - 'notification/*.pdf'
  workflow_dispatch:

jobs:
  process-job:
    runs-on: ubuntu-latest
    # --- YE LINES ADD KAREIN (SABSE ZAROORI) ---
    permissions:
      contents: write
    # ----------------------------------------
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - name: Run AI Script
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python scripts/process_pdf.py
      - name: Commit Updated Data
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add data/
          git commit -m "AI Update: New Job Details Added" || echo "No changes"
          git push
