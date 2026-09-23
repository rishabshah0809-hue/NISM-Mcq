"""
Builds questions.js from the NISM Series VIII 500-MCQ Word document.

Usage:
    python tools/build_questions.py "path/to/NISM_VIII_500_MCQ_Detailed_Explanations.docx"

Output: questions.js (in the project root) defining
    window.QUESTION_BANK  -> 500 question objects
    window.QUESTION_SETS  -> 10 arrays of 50 question ids (no overlap)
"""
import json
import random
import re
import sys
from pathlib import Path

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

NUM_SETS = 10
PER_SET = 50
SEED = 2026  # fixed seed -> the same sets every time the script is run

ROOT = Path(__file__).resolve().parent.parent
LETTERS = "abcd"

Q_RE = re.compile(r"^Q(\d+)\.\s*(.*)$", re.S)
OPT_RE = re.compile(r"^\(([a-d])\)\s*(.*)$", re.S)
ANS_RE = re.compile(r"^The correct answer is\s*✅?\s*\(([a-d])\)")
CHAP_RE = re.compile(r"^Chapter (\d+):\s*(.*)$")
KEY_CELL_RE = re.compile(r"^(\d+)\.\s*([a-d])$")


def body_items(document):
    """Yield ('p', text) / ('t', rows) in document order."""
    for el in document.element.body.iterchildren():
        tag = el.tag.split("}")[1]
        if tag == "p":
            yield "p", Paragraph(el, document).text.strip()
        elif tag == "tbl":
            rows = [[c.text.strip() for c in r.cells] for r in Table(el, document).rows]
            yield "t", rows


def parse(path):
    document = docx.Document(path)
    questions, master_key = [], {}
    chapter = (0, "")
    cur = None
    stage = None  # stem | options | why | notes

    def finish():
        if cur:
            questions.append(cur)

    for kind, val in body_items(document):
        if kind == "t":
            # Master answer key rows: "1. c", "2. c", ...
            if all(KEY_CELL_RE.match(c) for c in val[0] if c):
                for row in val:
                    for c in row:
                        m = KEY_CELL_RE.match(c)
                        if m:
                            master_key[int(m.group(1))] = LETTERS.index(m.group(2))
                continue
            if cur and val[0][:2] == ["Option", "Verdict"]:
                reasons = [""] * len(cur["options"])
                for row in val[1:]:
                    m = OPT_RE.match(row[0])
                    if m:
                        reasons[LETTERS.index(m.group(1))] = row[2]
                cur["reasons"] = reasons
                stage = "notes"
            continue

        text = val
        if not text:
            continue
        m = CHAP_RE.match(text)
        if m:
            finish()
            cur = None
            chapter = (int(m.group(1)), m.group(2).strip())
            continue
        m = Q_RE.match(text)
        if m:
            finish()
            cur = {
                "n": int(m.group(1)),
                "ch": chapter[0],
                "chapter": chapter[1],
                "q": m.group(2).strip(),
                "options": [],
                "answer": None,
                "why": [],
                "reasons": [],
                "notes": [],
            }
            stage = "stem"
            continue
        if cur is None:
            continue
        m = OPT_RE.match(text)
        if m and stage in ("stem", "options") and len(cur["options"]) < 4:
            cur["options"].append(m.group(2).strip())
            stage = "options"
            continue
        if stage == "stem":
            cur["q"] += "\n" + text
            continue
        m = ANS_RE.match(text)
        if m:
            cur["answer"] = LETTERS.index(m.group(1))
            stage = "why"
            continue
        if text == "Why?":
            continue
        if stage == "why":
            cur["why"].append(text)
        elif stage == "notes":
            cur["notes"].append(text)
    finish()
    return questions, master_key


def validate(questions, master_key):
    problems = []
    if len(questions) != NUM_SETS * PER_SET:
        problems.append(f"expected {NUM_SETS * PER_SET} questions, found {len(questions)}")
    nums = [q["n"] for q in questions]
    if len(set(nums)) != len(nums):
        problems.append("duplicate question numbers")
    for q in questions:
        tag = f"Q{q['n']}"
        if len(q["options"]) not in (2, 4):  # a few are True/False
            problems.append(f"{tag}: {len(q['options'])} options")
        if q["answer"] is None:
            problems.append(f"{tag}: no answer line")
        elif master_key and master_key.get(q["n"]) != q["answer"]:
            problems.append(f"{tag}: answer differs from master key")
        if len(q["reasons"]) != len(q["options"]) or not all(q["reasons"]):
            problems.append(f"{tag}: option-reason table incomplete")
    return problems


# Questions that build on the question just before them ("Same long call ...",
# "In the same collar ...", "Continuing ..."). Each one is kept in the same set
# as its predecessor and shown right after it.
FOLLOWS_PREVIOUS = {53, 60, 72, 78, 79, 104, 130, 162, 193, 214, 215, 270, 272, 273,
                    288, 290, 291, 296, 311, 314, 318, 322, 412, 435}


def make_sets(questions):
    """Split the bank into sets with no overlap. Linked questions travel together,
    and questions are dealt chapter by chapter so every set follows the
    syllabus weightage."""
    rng = random.Random(SEED)
    units = []  # each unit = a list of ids that must stay together, in order
    for q in sorted(questions, key=lambda q: q["n"]):
        if q["n"] in FOLLOWS_PREVIOUS and units and units[-1][-1] == q["n"] - 1:
            units[-1].append(q["n"])
        else:
            units.append([q["n"]])
    chapter_of = {q["n"]: q["ch"] for q in questions}

    sets = [[] for _ in range(NUM_SETS)]

    def size(s):
        return sum(len(u) for u in s)

    def chapter_count(s, ch):
        return sum(1 for u in s for qid in u if chapter_of[qid] == ch)

    def place(unit):
        # the set with the fewest questions from this chapter, then the emptiest
        # one that still has room (ties broken at random)
        ch = chapter_of[unit[0]]
        room = [s for s in sets if size(s) + len(unit) <= PER_SET]
        key = lambda s: (chapter_count(s, ch), size(s))
        best = min(key(s) for s in room)
        rng.choice([s for s in room if key(s) == best]).append(unit)

    groups = [u for u in units if len(u) > 1]
    singles = [u for u in units if len(u) == 1]
    rng.shuffle(groups)
    for u in groups:
        place(u)
    for ch in sorted({chapter_of[u[0]] for u in singles}):
        chunk = [u for u in singles if chapter_of[u[0]] == ch]
        rng.shuffle(chunk)
        for u in chunk:
            place(u)

    out = []
    for s in sets:
        rng.shuffle(s)  # mix chapters inside a set, like the real exam
        out.append([qid for unit in s for qid in unit])
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    questions, master_key = parse(sys.argv[1])
    problems = validate(questions, master_key)
    if problems:
        print("Validation problems:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    sets = make_sets(questions)
    flat = [qid for s in sets for qid in s]
    assert len(flat) == len(set(flat)) == len(questions), "sets overlap"
    assert all(len(s) == PER_SET for s in sets)
    for qid in FOLLOWS_PREVIOUS:  # linked questions sit right after their parent
        s = next(s for s in sets if qid in s)
        assert s.index(qid) > 0 and s[s.index(qid) - 1] == qid - 1, qid

    bank = {q["n"]: {k: v for k, v in q.items() if k != "n"} | {"id": q["n"]} for q in questions}
    out = ROOT / "questions.js"
    out.write_text(
        "/* Auto-generated by tools/build_questions.py - do not edit by hand. */\n"
        "window.QUESTION_BANK = " + json.dumps(bank, ensure_ascii=False) + ";\n"
        "window.QUESTION_SETS = " + json.dumps(sets) + ";\n",
        encoding="utf-8",
    )
    print(f"OK: {len(questions)} questions -> {NUM_SETS} sets of {PER_SET} -> {out}")
    for i, s in enumerate(sets, 1):
        chs = {}
        for qid in s:
            chs[bank[qid]["ch"]] = chs.get(bank[qid]["ch"], 0) + 1
        print(f"  Set {i:>2}: " + " ".join(f"C{c}:{n}" for c, n in sorted(chs.items())))


if __name__ == "__main__":
    main()
