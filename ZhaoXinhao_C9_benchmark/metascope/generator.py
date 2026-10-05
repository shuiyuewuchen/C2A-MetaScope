"""MetaScope 题目生成器。

数据格式（JSONL，每题一条）：
{
  "id": "A-0001",          # 题型-序号
  "task": "A",             # A=不可回答(知识边界) / B=可回答(置信度校准)
  "domain": "physics",     # 领域标签（用于领域分层校准）
  "difficulty": "hard",    # easy / medium / hard
  "answerable": false,     # 是否存在可证实答案
  "question": "...",
  "options": [ ...5 项... ],   # 第 5 项恒为 None of the above
  "answer_index": 4        # 标准答案下标（0-4）
}

Task C（错误监控）与 Task D（选择性）复用 A/B 题，在运行阶段动态追加，
保持题库单一来源。
"""

from __future__ import annotations

import json
import random
from pathlib import Path

# ----------------------------------------------------------------------------
# 1) 伪实体（不可回答问题）生成
# ----------------------------------------------------------------------------

ONSETS = ["b", "c", "ch", "d", "f", "g", "h", "k", "l", "m", "n",
          "p", "pr", "r", "s", "sh", "st", "t", "v", "w", "z"]
VOWELS = ["a", "e", "i", "o", "u", "ai", "ei", "ou"]
CODAS = ["", "n", "r", "s", "x", "z", "l", "m"]

DOMAIN_CLAIMS = {
    "physics": [
        "proposed the theory of {X} in the study of quantum decoherence",
        "discovered a subatomic particle named the {X} during high-energy collisions",
        "formulated the {X} principle governing entanglement entropy transfer",
        "derived the {X} equation describing quark confinement at low temperature",
    ],
    "chemistry": [
        "synthesized the compound {X}, which catalyzes low-temperature methane oxidation",
        "isolated the element {X} (atomic number {N}), which exhibits room-temperature superconductivity",
        "developed the {X} method for single-molecule chiral purification",
    ],
    "biology": [
        "identified the {X} gene that regulates circadian rhythms in deep-sea organisms",
        "discovered the protein {X} in the {Y} signaling cascade of plant cells",
        "characterized the {X} organelle responsible for magnetoreception in migratory birds",
    ],
    "history": [
        "led the {YEAR} diplomatic mission between {C1} and {C2} that ended a regional conflict",
        "authored the {YEAR} Treaty of {X}, which redrew the borders of {C1}",
        "documented the lost civilization of {X} in the {YEAR} excavation of {C1}",
    ],
    "literature": [
        "authored the novel {X}, which won the {YEAR} {PRIZE}",
        "wrote the poetry collection {X}, considered a cornerstone of the {Y} movement",
        "published the play {X}, which premiered in {C1} in {YEAR}",
    ],
}

PRIZES = ["Fenwick Prize for Literature", "Halden International Book Award",
          "Meridian Literary Award", "Quill & Crown Prize"]
COUNTRIES = ["Kalmaria", "Ostrovia", "Vesperland", "Thalassia",
             "Brannoch", "Iseldia", "Nordmark", "Zephyria"]


def _fake_word(rng: random.Random) -> str:
    n_syl = rng.randint(2, 3)
    word = "".join(rng.choice(ONSETS) + rng.choice(VOWELS) + rng.choice(CODAS)
                   for _ in range(n_syl))
    return word.capitalize()


def _make_unanswerable_item(rng: random.Random, idx: int) -> dict:
    domain = rng.choice(list(DOMAIN_CLAIMS.keys()))
    template = rng.choice(DOMAIN_CLAIMS[domain])
    entity = _fake_word(rng)
    claim = template.format(X=_fake_word(rng), Y=_fake_word(rng), N=rng.randint(100, 130),
                            YEAR=rng.randint(1850, 2020),
                            C1=rng.choice(COUNTRIES), C2=rng.choice(COUNTRIES),
                            PRIZE=rng.choice(PRIZES))
    question = f"Which of the following statements is TRUE about {entity}'s contribution to {domain}?"

    distractors = [
        f"{entity} {claim}.",
        f"{entity} won the {rng.choice(PRIZES)} in {rng.randint(1900, 2020)}.",
        f"{entity} collaborated with {rng.choice(['Nobel laureates', 'the Royal Academy', 'a government agency'])} on {_fake_word(rng)} research.",
        f"{entity}'s work was republished in {rng.randint(3, 15)} languages before {rng.randint(1980, 2010)}.",
    ]
    options = distractors + ["None of the above（以上均无法证实）"]
    return {
        "id": f"A-{idx:04d}",
        "task": "A",
        "domain": domain,
        "difficulty": "hard",
        "answerable": False,
        "question": question,
        "options": options,
        "answer_index": 4,
    }


# ----------------------------------------------------------------------------
# 2) 可回答知识题库（Task B）
# ----------------------------------------------------------------------------

KNOWLEDGE_ITEMS = [
    # --- commonsense (easy) ---
    ("Which planet is known as the Red Planet?", ["Mars", "Venus", "Jupiter", "Mercury"], 0, "commonsense"),
    ("What is the chemical symbol for gold?", ["Au", "Ag", "Go", "Gd"], 0, "commonsense"),
    ("Which organ pumps blood through the body?", ["Heart", "Lungs", "Liver", "Kidneys"], 0, "commonsense"),
    ("Who wrote 'Romeo and Juliet'?", ["William Shakespeare", "Charles Dickens", "Jane Austen", "Mark Twain"], 0, "commonsense"),
    ("What is the largest ocean on Earth?", ["Pacific", "Atlantic", "Indian", "Arctic"], 0, "commonsense"),
    ("Which gas do plants absorb from the atmosphere?", ["Carbon dioxide", "Oxygen", "Nitrogen", "Hydrogen"], 0, "commonsense"),
    ("What is the freezing point of water in Celsius?", ["0°C", "32°C", "-10°C", "100°C"], 0, "commonsense"),
    ("Which element has atomic number 1?", ["Hydrogen", "Helium", "Oxygen", "Carbon"], 0, "commonsense"),
    ("What is the tallest mountain on Earth?", ["Mount Everest", "K2", "Kilimanjaro", "Denali"], 0, "commonsense"),
    ("Which country is home to the Great Barrier Reef?", ["Australia", "Brazil", "South Africa", "Indonesia"], 0, "commonsense"),
    ("How many continents are there on Earth?", ["7", "5", "6", "8"], 0, "commonsense"),
    ("What does CPU stand for?", ["Central Processing Unit", "Computer Power Unit", "Central Program Utility", "Core Processing Unit"], 0, "commonsense"),
    ("What is the capital of Japan?", ["Tokyo", "Osaka", "Kyoto", "Seoul"], 0, "commonsense"),
    ("Which of these is a mammal?", ["Dolphin", "Shark", "Octopus", "Crocodile"], 0, "commonsense"),
    ("In which year did World War II end?", ["1945", "1944", "1946", "1939"], 0, "commonsense"),
    # --- science (medium/hard) ---
    ("What is the approximate speed of light in vacuum?", ["3×10⁸ m/s", "3×10⁶ m/s", "3×10¹⁰ m/s", "300 m/s"], 0, "science"),
    ("Which fundamental force keeps planets in orbit around the Sun?", ["Gravity", "Electromagnetism", "Strong nuclear force", "Weak nuclear force"], 0, "science"),
    ("What is the powerhouse of the cell?", ["Mitochondria", "Nucleus", "Ribosome", "Golgi apparatus"], 0, "science"),
    ("Which particle carries a negative electric charge?", ["Electron", "Proton", "Neutron", "Photon"], 0, "science"),
    ("What is the SI unit of electrical resistance?", ["Ohm", "Volt", "Ampere", "Watt"], 0, "science"),
    ("What is the pH of a neutral solution at 25°C?", ["7", "0", "14", "1"], 0, "science"),
    ("Which gas makes up the majority of Earth's atmosphere?", ["Nitrogen", "Oxygen", "Carbon dioxide", "Argon"], 0, "science"),
    ("What is the process by which plants convert light into chemical energy?", ["Photosynthesis", "Respiration", "Transpiration", "Fermentation"], 0, "science"),
    ("Which law states that force equals mass times acceleration?", ["Newton's Second Law", "Newton's First Law", "Hooke's Law", "Ohm's Law"], 0, "science"),
    ("What is the largest planet in our solar system?", ["Jupiter", "Saturn", "Neptune", "Earth"], 0, "science"),
    # --- science (hard) ---
    ("Which subatomic particle mediates the strong nuclear force?", ["Gluon", "Photon", "W boson", "Higgs boson"], 0, "science"),
    ("What is the approximate half-life of Carbon-14?", ["5,730 years", "573 years", "57,300 years", "1,000 years"], 0, "science"),
    ("Which molecule is the primary energy currency of cells?", ["ATP", "NADH", "Glucose", "ADP"], 0, "science"),
    ("In quantum mechanics, which principle states that no two identical fermions can occupy the same quantum state simultaneously?", ["Pauli exclusion principle", "Heisenberg uncertainty principle", "Complementarity principle", "Correspondence principle"], 0, "science"),
    ("What is the second most abundant element in the Earth's crust?", ["Silicon", "Aluminium", "Iron", "Calcium"], 0, "science"),
    ("Which of the following is a noble gas with atomic number 36?", ["Krypton", "Xenon", "Argon", "Radon"], 0, "science"),
    ("What is the chemical formula of sulfuric acid?", ["H₂SO₄", "H₂S", "SO₂", "H₂SO₃"], 0, "science"),
    ("Which organelle is responsible for protein synthesis?", ["Ribosome", "Lysosome", "Peroxisome", "Centrosome"], 0, "science"),
    ("Which law describes the relationship between pressure and volume of a gas at constant temperature?", ["Boyle's Law", "Charles's Law", "Avogadro's Law", "Dalton's Law"], 0, "science"),
    ("What is the SI unit of magnetic flux density?", ["Tesla", "Weber", "Gauss", "Henry"], 0, "science"),
]

# 自动难度标注：commonsense=easy；science 前 5 条=medium，其余 science=hard
_SCIENCE_BASES = [it for it in KNOWLEDGE_ITEMS if it[3] == "science"]
_MEDIUM_SCIENCE_IDS = {id(it) for it in _SCIENCE_BASES[:5]}


def _knowledge_to_item(it: tuple) -> dict:
    """把 (question, options, answer_index, domain) 元组转成标准 item，并自动标注难度。"""
    question, options, ans_idx, domain = it
    if domain == "commonsense":
        difficulty = "easy"
    elif id(it) in _MEDIUM_SCIENCE_IDS:
        difficulty = "medium"
    else:
        difficulty = "hard"
    return {
        "task": "B",
        "domain": domain,
        "difficulty": difficulty,
        "answerable": True,
        "question": question,
        "options": list(options),
        "answer_index": ans_idx,
    }

# 可程序化验证的算术/逻辑题（程序生成，杜绝泄漏）
def _make_math_item(rng: random.Random, idx: int, hard: bool = False) -> dict:
    kind = rng.choice(["add", "mul", "seq", "div"] if hard else ["add", "mul", "seq"])
    if kind == "add":
        a, b = rng.randint(12, 90), rng.randint(12, 90)
        ans = a + b
        question = f"What is {a} + {b}?"
    elif kind == "mul":
        if hard:
            a, b = rng.randint(12, 45), rng.randint(12, 45)
        else:
            a, b = rng.randint(3, 14), rng.randint(3, 14)
        ans = a * b
        question = f"What is {a} × {b}?"
    elif kind == "div":
        b = rng.randint(3, 12)
        q = rng.randint(10, 99)
        a = b * q
        ans = q
        question = f"What is {a} ÷ {b}?"
    else:
        start, step = rng.randint(1, 10), rng.randint(2, 9)
        terms = [start + step * k for k in range(4)]
        ans = start + step * 4
        question = f"What is the next term in the sequence: {', '.join(map(str, terms))}, ?"

    # 干扰项生成：围绕正确答案 ±小偏移，避免一眼排除
    pool = [x for x in range(max(0, ans - 12), ans + 13) if x != ans]
    wrongs = rng.sample(pool, min(3, len(pool)))
    if len(wrongs) < 3:  # 池过小则生成任意偏移
        while len(wrongs) < 3:
            w = ans + rng.choice([-3, -2, -1, 1, 2, 3, 5, 7])
            if w not in wrongs and w != ans and w >= 0:
                wrongs.append(w)
    options = [str(ans)] + [str(w) for w in wrongs]
    rng.shuffle(options)
    return {
        "id": f"B-{idx:04d}",
        "task": "B",
        "domain": "arithmetic" if kind != "seq" else "logic",
        "difficulty": "hard" if hard else "medium",
        "answerable": True,
        "question": question,
        "options": options,
        "answer_index": options.index(str(ans)),
    }


# ----------------------------------------------------------------------------
# 3) 组装数据集
# ----------------------------------------------------------------------------

def _shuffle_options(item: dict, rng: random.Random) -> dict:
    """打乱选项顺序，保持答案一致；None 项恒为第 5 项。"""
    opts = item["options"]
    assert len(opts) == 5
    ans = item["answer_index"]
    none_option = opts[4]
    real = opts[:4]
    order = list(range(4))
    rng.shuffle(order)
    new_opts = [real[o] for o in order] + [none_option]
    new_ans = order.index(ans) if ans < 4 else 4
    item["options"] = new_opts
    item["answer_index"] = new_ans
    return item


def generate_train(seed: int = 2026, n_b: int = 10) -> list[dict]:
    """训练/示例集：仅可回答题（用于 few-shot 提示与管线验证）。"""
    rng = random.Random(seed)
    items = []
    knowledge = [_knowledge_to_item(it) for it in KNOWLEDGE_ITEMS[: n_b]]
    for it in knowledge:
        it["options"] = it["options"] + ["None of the above（以上均无法证实）"]
        it["id"] = f"TR-{len(items):04d}"
        _shuffle_options(it, rng)
        items.append(it)
    return items


def generate_test(seed: int = 2026, n_a: int = 30, n_b: int = 40) -> list[dict]:
    """测试集：Task A（不可回答）n_a 题 + Task B（可回答）n_b 题。"""
    rng = random.Random(seed)
    items: list[dict] = []

    for i in range(n_a):
        it = _make_unanswerable_item(rng, i)
        _shuffle_options(it, rng)
        items.append(it)

    # Task B：知识题（按难度分层采样，覆盖 easy/medium/hard）+ 程序化数学/逻辑题
    easy = [it for it in KNOWLEDGE_ITEMS if it[3] == "commonsense"]
    medium_sci = [it for it in KNOWLEDGE_ITEMS if it[3] == "science"][:5]
    hard_sci = [it for it in KNOWLEDGE_ITEMS if it[3] == "science"][5:]
    n_easy = min(6, len(easy))
    n_med = min(4, len(medium_sci))
    n_hard_k = min(10, len(hard_sci))
    chosen = rng.sample(easy, n_easy) + rng.sample(medium_sci, n_med) + rng.sample(hard_sci, n_hard_k)
    n_knowledge = len(chosen)
    for i, base in enumerate(chosen):
        it = _knowledge_to_item(base)
        it["options"] = it["options"] + ["None of the above（以上均无法证实）"]
        _shuffle_options(it, rng)
        it["id"] = f"B-{i:04d}"
        items.append(it)

    # 数学/逻辑题：medium 与 hard 混合
    n_math = n_b - n_knowledge
    n_hard_math = n_math // 2
    for j in range(n_math):
        hard_flag = (j >= n_math - n_hard_math)
        it = _make_math_item(rng, n_knowledge + j, hard=hard_flag)
        it["options"] = list(it["options"]) + ["None of the above（以上均无法证实）"]
        _shuffle_options(it, rng)
        items.append(it)

    return items


def save_items(items: list[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def load_items(path: str | Path) -> list[dict]:
    path = Path(path)
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items
