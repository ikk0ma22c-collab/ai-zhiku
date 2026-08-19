import dashscope
from dotenv import load_dotenv
import os


load_dotenv()

def rerank_documents(query: str, documents: list[str]) -> list[float]:

    dashscope.api_key = os.getenv("OPENAI_API_KEY")
    response = dashscope.TextReRank.call(
        model=os.getenv("TEXT_RERANK_MODEL"),
        query=query,
        documents=documents,
        top_n=len(documents),
        return_documents=False,
        instruct=os.getenv("TEXT_RERANK_INSTRUCT"),
    )

    status_code = response.get("status_code")
    if status_code != 200:
        message = response.get("message")
        raise RuntimeError(f"DashScope rerank 调用失败: {message}")

    results = response.output.get("results", [])
    scores = [0.0] * len(documents)
    for item in results:
        index = item.get("index")
        score = item.get("relevance_score")
        scores[int(index)] = float(score)
    return scores