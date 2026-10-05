# NISM Mock Tests (Vexy)

500 NISM Series VIII (Equity Derivatives) MCQs split into **10 sets of 50**, with no question repeated across sets.
Every set gets 1 hr 10 min, a live timer and auto-submit, a score card and a full answer key with explanations.

The same site also includes **NISM Series XV – Research Analyst**. It has six full 100-question papers (80 MCQs and 20 case-study questions), plus one 100-question Case Study Mastery Test. The Series XV papers are 2 hours, use −0.25 negative marking, and have no repeated question across the seven papers.

## Use it
Open `index.html` in any browser (double-click works, no server needed).
Use the certification selector at the top to switch between Equity Derivatives and Research Analyst.
Progress and results are saved in that browser.

## Files
| File | What it is |
|---|---|
| `index.html` | The whole app: home, exam screen, score card, answer key |
| `questions.js` | Generated question bank and the 10 sets (don't edit by hand) |
| `tools/build_questions.py` | Rebuilds `questions.js` from the Word document |
| `questions-ra.js` | Generated Series XV question bank, caselets and seven non-overlapping papers |
| `tools/build_ra_questions.py` | Rebuilds `questions-ra.js` from the Research Analyst PDF |

## Rebuild the questions
```bash
pip install python-docx
python tools/build_questions.py "path/to/NISM_VIII_500_MCQ_Detailed_Explanations.docx"
```
The script checks every answer against the master answer key at the end of the document.
It keeps follow-up questions ("Same long call…", "In the same collar…") in the same set as the question they build on,
and spreads each chapter evenly across the 10 sets.
