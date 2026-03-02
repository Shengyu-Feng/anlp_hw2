import json
import re
import requests
from retrieve import _corpus


# ── Config ────────────────────────────────────────────────────────────────────

QUERIES_PATH = "questions.json"
RETRIEVED_PATH = "question_retrieved.json"
OLLAMA_MODEL = "qwen2.5:14b"
save_path = "system_output_3.json"
TOP_K = 6

TEMPLATE = """
You need to answer the following quiz questions. Some reference information is provided to help you. But if the information is not helpful, answer it via your own memory as best as you can. Your final answer should be accurate. Put your final answer in  <answer> YOUR ANSWER </answer>.

Your final answer should be a quiz-style answer ready for grading. It should be **a complete sentence rather than just few words**, without any irrelevant information to the question.

# Quiz Question
{question}

# Reference Information
{info}

# Answer
"""

# ── Ollama ────────────────────────────────────────────────────────────────────

def ollama_generate(prompt: str, model: str = OLLAMA_MODEL) -> str:
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["response"]


def parse_answer(response: str) -> str:
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", response, re.DOTALL)
    return match.group(1) if match else response


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    queries = json.load(open(QUERIES_PATH))
    retrieved = json.load(open(RETRIEVED_PATH))
    submission = {}#"andrewid": "Nidoran"}

    for q in queries:
        qid = q['id']
        question = q['question']

        indices = retrieved[qid]["dense"] + retrieved[qid]["sparse"]
        # deduplicate, preserve order
        seen = set()
        docs = []
        for i in indices:
            if i not in seen:
                seen.add(i)
                docs.append(_corpus[i])

        info = "\n\n".join(docs[:TOP_K])
        prompt = TEMPLATE.format(info=info, question=question)
        response = ollama_generate(prompt)
        answer = parse_answer(response)
        #print(f"{question}\n→ {answer}\n")
        submission[qid] = answer

    with open(save_path, "w") as f:
        json.dump(submission, f, indent=2)