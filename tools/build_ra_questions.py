"""Build the NISM Series XV Research Analyst question bank from the supplied PDF.

Usage:
  python tools/build_ra_questions.py path/to/NISM_XV_Research_Analyst_Question_Bank.pdf

Creates questions-ra.js.  The final section contains six full, non-overlapping
100-question practice papers (80 MCQs + five 4-question case studies) and one
100-question case-study mastery paper using every remaining source question.
"""

import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent.parent
LETTERS = "abcd"
RNG = random.Random(20261005)

CHAPTER = re.compile(r"^Chapter\s+(\d+):\s*(.+?)(?:\s*\(Q\d+.*)?$")
MCQ = re.compile(r"^Q(\d+)\.\s*(.*)$")
CASE = re.compile(r"^Case\s+(\d+):\s*(.+)$")
CASE_Q = re.compile(r"^(\d+)\.(\d+)\s+(.*)$")
OPTION = re.compile(r"^([a-d])\)\s*(.*)$", re.I)
MCQ_ANSWER = re.compile(r"^Q(\d+)\.\s*Answer:\s*([a-d])\)\s*(.*)$", re.I)
CASE_ANSWER = re.compile(r"^(\d+)\.(\d+)\s+Answer:\s*([a-d])\)\s*(.*)$", re.I)


def text_lines(pdf_path):
    reader = PdfReader(pdf_path)
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Headers/footers are not content and break explanation grouping.
    lines = []
    for line in raw.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line or line.startswith("NISM Series XV Research Analyst - Practice Question Bank") or line == "Page":
            continue
        if re.fullmatch(r"Page \d+", line):
            continue
        lines.append(line)
    return lines


def clean(parts):
    return " ".join(p.strip() for p in parts if p.strip())


def parse(pdf_path):
    lines = text_lines(pdf_path)
    part_a = [i for i, line in enumerate(lines) if line == "Part A: 500 Multiple Choice Questions"][-1]
    part_b = next(i for i, line in enumerate(lines[part_a + 1:], part_a + 1) if line == "Part B: 50 Case Studies")
    mcqs = parse_mcqs(lines[part_a:part_b])
    cases = parse_cases(lines[part_b:])
    validate(mcqs, cases)
    return mcqs, cases


def parse_mcqs(lines):
    questions = {}
    chapter = (0, "")
    mode = "question"
    current = None
    explanation_id = None

    def finish_question():
        nonlocal current
        if current and current["id"] not in questions:
            questions[current["id"]] = current
        current = None

    for line in lines:
        ch = CHAPTER.match(line)
        if ch:
            finish_question()
            chapter = (int(ch.group(1)), ch.group(2).replace("Answers and explanations", "").strip())
            mode = "answers" if "Answers and explanations" in line else "question"
            continue

        if mode == "question":
            hit = MCQ.match(line)
            if hit:
                finish_question()
                qid, stem = int(hit.group(1)), hit.group(2)
                current = {"id": f"m{qid}", "source": qid, "ch": chapter[0], "chapter": chapter[1],
                           "q": stem, "options": [], "answer": None, "why": [], "reasons": [], "notes": []}
                continue
            if not current:
                continue
            opt = OPTION.match(line)
            if opt and len(current["options"]) < 4:
                current["options"].append(opt.group(2))
            elif len(current["options"]) == 0:
                current["q"] = clean([current["q"], line])
            continue

        answer = MCQ_ANSWER.match(line)
        if answer:
            explanation_id = int(answer.group(1))
            q = questions.get(f"m{explanation_id}")
            if q:
                q["answer"] = LETTERS.index(answer.group(2).lower())
                q["why"] = [answer.group(3)] if answer.group(3) else []
            continue
        if explanation_id is not None:
            q = questions.get(f"m{explanation_id}")
            if q:
                q["why"].append(line)

    finish_question()
    for q in questions.values():
        q["why"] = [clean(q["why"])]
        q["reasons"] = [
            q["why"][0] if idx == q["answer"] else "This option does not match the explanation and result given above."
            for idx in range(len(q["options"]))
        ]
    return questions


def parse_cases(lines):
    questions = {}
    chapter = (0, "")
    current_case = None
    current_q = None
    in_solutions = False
    answer_id = None

    def finish_q():
        nonlocal current_q
        if current_q and current_q["id"] not in questions:
            questions[current_q["id"]] = current_q
        current_q = None

    for line in lines:
        ch = CHAPTER.match(line)
        if ch:
            finish_q()
            chapter = (int(ch.group(1)), ch.group(2).strip())
            continue
        case = CASE.match(line)
        if case:
            finish_q()
            case_no, title = int(case.group(1)), case.group(2)
            current_case = {"no": case_no, "title": title, "text": []}
            in_solutions = False
            answer_id = None
            continue
        if line.startswith("Solution to Case"):
            finish_q()
            in_solutions = True
            answer_id = None
            continue
        if not current_case:
            continue

        if not in_solutions:
            qhit = CASE_Q.match(line)
            if qhit:
                finish_q()
                case_no, sub_no = int(qhit.group(1)), int(qhit.group(2))
                stem = qhit.group(3)
                current_q = {"id": f"c{case_no}_{sub_no}", "source": f"{case_no}.{sub_no}",
                             "ch": chapter[0], "chapter": chapter[1], "q": stem, "options": [],
                             "answer": None, "why": [], "reasons": [], "notes": [],
                             "case": {"number": case_no, "title": current_case["title"],
                                      "text": clean(current_case["text"])}}
                continue
            opt = OPTION.match(line)
            if current_q and opt and len(current_q["options"]) < 4:
                current_q["options"].append(opt.group(2))
            elif current_q is None:
                current_case["text"].append(line)
            elif len(current_q["options"]) == 0:
                current_q["q"] = clean([current_q["q"], line])
            continue

        answer = CASE_ANSWER.match(line)
        if answer:
            case_no, sub_no = int(answer.group(1)), int(answer.group(2))
            answer_id = f"c{case_no}_{sub_no}"
            q = questions.get(answer_id)
            if q:
                q["answer"] = LETTERS.index(answer.group(3).lower())
                q["why"] = [answer.group(4)] if answer.group(4) else []
            continue
        if answer_id and answer_id in questions:
            questions[answer_id]["why"].append(line)

    finish_q()
    for q in questions.values():
        q["why"] = [clean(q["why"])]
        q["reasons"] = [
            q["why"][0] if idx == q["answer"] else "This option does not match the calculation or conclusion shown in the case solution."
            for idx in range(len(q["options"]))
        ]
    return questions


def validate(mcqs, cases):
    problems = []
    if len(mcqs) != 500:
        problems.append(f"expected 500 MCQs, found {len(mcqs)}")
    if len(cases) != 200:
        problems.append(f"expected 200 case questions, found {len(cases)}")
    for q in list(mcqs.values()) + list(cases.values()):
        if len(q["options"]) not in (2, 4):
            problems.append(f"{q['id']}: expected 2 or 4 options, found {len(q['options'])}")
        if q["answer"] is None:
            problems.append(f"{q['id']}: missing answer")
        if not q["why"] or not q["why"][0]:
            problems.append(f"{q['id']}: missing explanation")
    if problems:
        raise ValueError("\n".join(problems[:100]))


def make_sets(mcqs, cases):
    mcq_by_ch = defaultdict(list)
    for q in mcqs.values():
        mcq_by_ch[q["ch"]].append(q["id"])
    for pool in mcq_by_ch.values():
        RNG.shuffle(pool)

    mcq_papers = [[] for _ in range(6)]
    # Deal chapter-wise, so every paper is broad and follows the syllabus.
    for pool in mcq_by_ch.values():
        for idx, qid in enumerate(pool[:480]):
            if len(mcq_papers[idx % 6]) < 80:
                mcq_papers[idx % 6].append(qid)
            else:
                target = min(range(6), key=lambda i: len(mcq_papers[i]))
                mcq_papers[target].append(qid)
    all_mcq = list(mcqs)
    assigned = {qid for paper in mcq_papers for qid in paper}
    remaining_mcq = [qid for qid in all_mcq if qid not in assigned]
    # Normalize each full paper to exactly 80 questions.
    spill = []
    for paper in mcq_papers:
        while len(paper) > 80:
            spill.append(paper.pop())
    remaining_mcq.extend(spill)
    for paper in mcq_papers:
        while len(paper) < 80:
            paper.append(remaining_mcq.pop())
        RNG.shuffle(paper)

    by_case = defaultdict(list)
    for q in cases.values():
        by_case[q["case"]["number"]].append(q["id"])
    case_groups = [by_case[i] for i in sorted(by_case)]
    papers = []
    for i in range(6):
        cases_for_paper = case_groups[i * 5:(i + 1) * 5]
        papers.append(mcq_papers[i] + [qid for group in cases_for_paper for qid in group])
    # Remaining 20 MCQs and 20 case studies make a 100-question mastery paper.
    papers.append(remaining_mcq + [qid for group in case_groups[30:] for qid in group])
    if not all(len(p) == 100 for p in papers):
        raise ValueError("could not produce 100-question papers")
    flat = [qid for paper in papers for qid in paper]
    if len(flat) != len(set(flat)) or len(flat) != 700:
        raise ValueError("question overlap while making sets")
    return papers


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    mcqs, cases = parse(sys.argv[1])
    bank = mcqs | cases
    sets = make_sets(mcqs, cases)
    payload = {
        "id": "ra", "name": "NISM Series XV: Research Analyst Certification Examination - 2026",
        "shortName": "NISM Series XV: Research Analyst", "durationMinutes": 120,
        "passPct": 60, "negativeMark": 0.25, "bank": bank, "sets": sets,
        "setNames": [f"Full Mock Test - Set {i}" for i in range(1, 7)] + ["Case Study Mastery Test"],
        "setKinds": ["Full Mock Test"] * 6 + ["Case Study Practice"],
    }
    output = ROOT / "questions-ra.js"
    output.write_text("window.RA_EXAM = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"Built {output}: {len(mcqs)} MCQs, {len(cases)} case questions, {len(sets)} non-overlapping papers")


if __name__ == "__main__":
    main()
