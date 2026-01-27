#!/usr/bin/env python3
import json
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from tqdm import tqdm
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from llm_config import (
    OPENAI_API_KEY, OPENAI_MODEL, LLM_GT_CONFIG,
    DATA_DIR, RESULTS_DIR, LLM_GT_OUTPUT
)

from openai import OpenAI

@dataclass
class SimilarityJudgment:
    candidate_id: str
    relevance_score: int
    reasoning: str
    common_concepts: List[str]

class MathItemJudge:
    POINTWISE_PROMPT = """당신은 수학 교육 전문가입니다. 두 수학 문항의 유사성을 평가해주세요.

## 평가 기준
- 5점: 동일한 수학적 개념, 거의 같은 유형의 문제
- 4점: 동일한 개념, 유사한 풀이 접근법
- 3점: 관련된 개념, 비슷한 문제 구조
- 2점: 약한 관련성 (같은 단원이지만 다른 유형)
- 1점: 관련 없음

## 쿼리 문항
{query}

## 후보 문항
{candidate}

## 응답 형식 (JSON만 출력)
{{"score": 1-5, "concepts": ["공통개념1", "공통개념2"], "reason": "판단 근거 1문장"}}"""

    LISTWISE_PROMPT = """당신은 수학 교육 전문가입니다. 쿼리 문항과 가장 유사한 순서로 후보들을 정렬하세요.

## 유사성 기준
- 동일한 수학적 개념을 다루는가
- 풀이 접근 방식이 비슷한가
- 학생이 비슷한 실수를 할 가능성이 있는가

## 쿼리 문항
{query}

## 후보 문항들
{candidates}

## 응답 형식 (JSON만 출력)
상위 5개만 유사도 순으로:
{{"rankings": [{{"id": "문항ID", "score": 1-5, "reason": "1문장"}}]}}"""

    def __init__(self, model: str = OPENAI_MODEL):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def pointwise_score(self, query: str, candidate: str, candidate_id: str) -> Optional[SimilarityJudgment]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": self.POINTWISE_PROMPT.format(
                    query=query, candidate=candidate
                )}],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.1
            )
            
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens
            
            result = json.loads(response.choices[0].message.content)
            return SimilarityJudgment(
                candidate_id=candidate_id,
                relevance_score=result.get("score", 1),
                reasoning=result.get("reason", ""),
                common_concepts=result.get("concepts", [])
            )
        except Exception as e:
            print(f"Error scoring {candidate_id}: {e}")
            return None

    def listwise_rank(self, query: str, candidates: List[Dict]) -> List[SimilarityJudgment]:
        candidates_text = "\n\n".join([
            f"[{c['id'][:12]}]\n{c['question'][:300]}" 
            for c in candidates[:10]
        ])
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": self.LISTWISE_PROMPT.format(
                    query=query, candidates=candidates_text
                )}],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.1
            )
            
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens
            
            result = json.loads(response.choices[0].message.content)
            rankings = result.get("rankings", [])
            
            judgments = []
            for r in rankings[:5]:
                full_id = next((c['id'] for c in candidates if c['id'].startswith(r['id'])), r['id'])
                judgments.append(SimilarityJudgment(
                    candidate_id=full_id,
                    relevance_score=r.get("score", 3),
                    reasoning=r.get("reason", ""),
                    common_concepts=[]
                ))
            return judgments
        except Exception as e:
            print(f"Listwise ranking error: {e}")
            return []

    def get_cost_estimate(self) -> Dict:
        input_cost = (self.total_input_tokens / 1_000_000) * 0.15
        output_cost = (self.total_output_tokens / 1_000_000) * 0.60
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(input_cost + output_cost, 4)
        }


def load_test_items() -> Dict[str, Dict]:
    with open(DATA_DIR / "test_items.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['id']: item for item in data['items']}

def load_embeddings() -> Dict[str, np.ndarray]:
    with open(RESULTS_DIR / "qwen_embeddings.json", 'r') as f:
        data = json.load(f)
    return {k: np.array(v) for k, v in data['embeddings'].items()}

def get_embedding_candidates(query_id: str, embeddings: Dict, k: int = 20) -> List[str]:
    query_emb = embeddings[query_id]
    similarities = []
    for other_id, other_emb in embeddings.items():
        if other_id != query_id:
            sim = np.dot(query_emb, other_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(other_emb))
            similarities.append((other_id, sim))
    similarities.sort(key=lambda x: -x[1])
    return [s[0] for s in similarities[:k]]

def categorize_item(item: Dict) -> str:
    has_image = item.get('has_image', False)
    has_latex = len(item.get('content', {}).get('question_latex', [])) > 0
    if has_image:
        return "image"
    elif has_latex:
        return "latex"
    return "text_only"


def main():
    print("=" * 60)
    print("LLM Ground Truth Generation")
    print(f"Model: {OPENAI_MODEL}")
    print("=" * 60)
    
    print("\n[1/4] Loading data...")
    items = load_test_items()
    embeddings = load_embeddings()
    print(f"      Items: {len(items)}, Embeddings: {len(embeddings)}")
    
    judge = MathItemJudge()
    ground_truth = []
    
    print(f"\n[2/4] Generating Ground Truth using LLM...")
    
    for query_id in tqdm(list(items.keys()), desc="Processing queries"):
        query_item = items[query_id]
        query_text = query_item['content']['question']
        
        candidate_ids = get_embedding_candidates(query_id, embeddings, k=LLM_GT_CONFIG["candidates_per_query"])
        candidates = [{"id": cid, "question": items[cid]['content']['question']} for cid in candidate_ids]
        
        judgments = judge.listwise_rank(query_text, candidates)
        
        if len(judgments) < 5:
            for cid in candidate_ids[:5]:
                if not any(j.candidate_id == cid for j in judgments):
                    judgment = judge.pointwise_score(query_text, items[cid]['content']['question'], cid)
                    if judgment:
                        judgments.append(judgment)
        
        relevant_items = []
        for j in judgments:
            if j.relevance_score >= LLM_GT_CONFIG["min_relevance_score"]:
                relevant_items.append({
                    "id": j.candidate_id,
                    "relevance": j.relevance_score,
                    "reasoning": j.reasoning,
                    "concepts": j.common_concepts
                })
        
        relevant_items = relevant_items[:LLM_GT_CONFIG["top_k_final"]]
        
        ground_truth.append({
            "query_id": query_id,
            "query_category": categorize_item(query_item),
            "relevant_items": relevant_items
        })
    
    print(f"\n[3/4] Saving results...")
    
    cost_info = judge.get_cost_estimate()
    total_pairs = sum(len(gt['relevant_items']) for gt in ground_truth)
    
    output_data = {
        "metadata": {
            "total_queries": len(ground_truth),
            "total_pairs": total_pairs,
            "generation_method": f"LLM-as-a-Judge ({OPENAI_MODEL})",
            "config": LLM_GT_CONFIG,
            "cost": cost_info
        },
        "ground_truth": ground_truth
    }
    
    with open(LLM_GT_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"      Saved: {LLM_GT_OUTPUT}")
    
    print(f"\n[4/4] Summary")
    print("=" * 60)
    print(f"  Queries: {len(ground_truth)}")
    print(f"  Total pairs: {total_pairs}")
    print(f"  Avg relevant items per query: {total_pairs/len(ground_truth):.1f}")
    print(f"  Input tokens: {cost_info['input_tokens']:,}")
    print(f"  Output tokens: {cost_info['output_tokens']:,}")
    print(f"  Estimated cost: ${cost_info['estimated_cost_usd']:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
