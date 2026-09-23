# NISM Series VIII – Mock Tests (Vexy)

500 NISM Series VIII (Equity Derivatives) MCQs split into **10 sets of 50**, with no question repeated across sets.
Every set gets 1 hr 10 min, a live timer and auto-submit, a score card and a full answer key with explanations.

## Use it
Open `index.html` in any browser (double-click works, no server needed).
Progress and results are saved in that browser.

## Files
| File | What it is |
|---|---|
| `index.html` | The whole app: home, exam screen, score card, answer key |
| `questions.js` | Generated question bank and the 10 sets (don't edit by hand) |
| `tools/build_questions.py` | Rebuilds `questions.js` from the Word document |

## Rebuild the questions
```bash
pip install python-docx
python tools/build_questions.py "path/to/NISM_VIII_500_MCQ_Detailed_Explanations.docx"
```
The script checks every answer against the master answer key at the end of the document.
It keeps follow-up questions ("Same long call…", "In the same collar…") in the same set as the question they build on,
and spreads each chapter evenly across the 10 sets.
