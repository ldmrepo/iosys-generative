#!/usr/bin/env python3
"""
Task #2 & #3: GPT-4o를 사용한 이미지 기반 Ground Truth 생성
두 문항의 텍스트와 이미지를 함께 보고 유사도를 판단
"""
import json
import base64
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio

# Load environment
load_dotenv()

POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
DATA_DIR = POC_DIR / "data"

# OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_TEMPLATE = """두 수학 문항의 유사도를 평가하세요.

## 문항 A
{text_a}

## 문항 B
{text_b}

## 평가 기준 (각 1-5점)
1. **개념 유사도 (concept_score)**: 같은 수학 개념을 다루는가?
   - 5: 동일한 개념 (예: 둘 다 일차함수의 기울기)
   - 3: 관련된 개념 (예: 일차함수와 이차함수)
   - 1: 다른 개념 (예: 함수와 도형)

2. **이미지 유사도 (image_score)**: 이미지(그래프, 도형, 표 등)가 유사한가?
   - 5: 거의 동일한 형태/구조
   - 3: 비슷한 유형이지만 다른 내용
   - 1: 완전히 다른 유형의 이미지

3. **풀이 유사도 (solution_score)**: 비슷한 방법으로 풀 수 있는가?
   - 5: 동일한 풀이 전략
   - 3: 일부 단계가 유사
   - 1: 완전히 다른 풀이 방법

4. **종합 유사도 (overall_score)**: 전체적으로 얼마나 유사한가?
   - 5: 매우 유사 (거의 같은 문제)
   - 4: 유사 (같은 유형의 문제)
   - 3: 보통 (일부 유사점 있음)
   - 2: 약간 유사 (약간의 관련성)
   - 1: 유사하지 않음

## 출력 형식 (JSON만 출력, 다른 텍스트 없이)
{{"concept_score": 숫자, "image_score": 숫자, "solution_score": 숫자, "overall_score": 숫자, "reasoning": "판단 근거 (1-2문장)"}}"""


def encode_image(image_path: str) -> str:
    """이미지를 base64로 인코딩"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """이미지 MIME 타입 반환"""
    ext = Path(image_path).suffix.lower()
    return {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }.get(ext, 'image/png')


async def evaluate_pair(pair: dict, semaphore: asyncio.Semaphore) -> dict:
    """단일 쌍 평가"""
    async with semaphore:
        item_a = pair['item_a']
        item_b = pair['item_b']

        # 프롬프트 생성
        prompt = PROMPT_TEMPLATE.format(
            text_a=item_a['text'],
            text_b=item_b['text']
        )

        # 이미지 인코딩
        try:
            img_a_b64 = encode_image(item_a['image_path'])
            img_b_b64 = encode_image(item_b['image_path'])
            img_a_type = get_image_media_type(item_a['image_path'])
            img_b_type = get_image_media_type(item_b['image_path'])
        except Exception as e:
            return {
                'item_a_id': item_a['id'],
                'item_b_id': item_b['id'],
                'error': f"Image encoding error: {str(e)}"
            }

        # API 호출
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                max_tokens=300,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "문항 A의 이미지:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{img_a_type};base64,{img_a_b64}",
                                "detail": "low"
                            }
                        },
                        {
                            "type": "text",
                            "text": "문항 B의 이미지:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{img_b_type};base64,{img_b_b64}",
                                "detail": "low"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # 응답 파싱
            content = response.choices[0].message.content.strip()

            # JSON 추출
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)

            return {
                'item_a_id': item_a['id'],
                'item_b_id': item_b['id'],
                'concept_score': result.get('concept_score', 0),
                'image_score': result.get('image_score', 0),
                'solution_score': result.get('solution_score', 0),
                'overall_score': result.get('overall_score', 0),
                'reasoning': result.get('reasoning', ''),
                'embedding_similarity': pair.get('embedding_similarity', 0),
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                }
            }

        except json.JSONDecodeError as e:
            return {
                'item_a_id': item_a['id'],
                'item_b_id': item_b['id'],
                'error': f"JSON parse error: {str(e)}",
                'raw_response': content if 'content' in dir() else None
            }
        except Exception as e:
            return {
                'item_a_id': item_a['id'],
                'item_b_id': item_b['id'],
                'error': str(e)
            }


async def main():
    print("=" * 60)
    print("GPT-4o 이미지 기반 Ground Truth 생성")
    print("=" * 60)

    # 쌍 데이터 로드
    print("\n[1/3] 데이터 로드...")
    with open(DATA_DIR / "image_pairs_for_gt.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    pairs = data['pairs']
    print(f"      비교 쌍: {len(pairs)}개")

    # 비용 추정
    estimated_tokens = len(pairs) * 2500  # 프롬프트 + 이미지 + 출력
    estimated_cost = (estimated_tokens / 1_000_000) * 5 + (len(pairs) * 200 / 1_000_000) * 15
    print(f"      예상 토큰: ~{estimated_tokens:,}")
    print(f"      예상 비용: ~${estimated_cost:.2f}")

    # 동시 요청 제한
    semaphore = asyncio.Semaphore(5)  # 동시 5개 요청

    # API 호출
    print("\n[2/3] GPT-4o API 호출...")
    tasks = [evaluate_pair(pair, semaphore) for pair in pairs]
    results = await tqdm_asyncio.gather(*tasks, desc="Evaluating pairs")

    # 결과 분석
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]

    print(f"\n      성공: {len(successful)}/{len(pairs)}")
    print(f"      실패: {len(failed)}")

    if successful:
        # 토큰 사용량 집계
        total_prompt = sum(r['usage']['prompt_tokens'] for r in successful)
        total_completion = sum(r['usage']['completion_tokens'] for r in successful)
        actual_cost = (total_prompt / 1_000_000) * 5 + (total_completion / 1_000_000) * 15

        print(f"      총 토큰: {total_prompt + total_completion:,}")
        print(f"      실제 비용: ${actual_cost:.2f}")

        # 점수 분포
        overall_scores = [r['overall_score'] for r in successful]
        print(f"\n      Overall Score 분포:")
        for score in range(1, 6):
            count = overall_scores.count(score)
            print(f"        {score}점: {count}개 ({count/len(overall_scores)*100:.1f}%)")

    # Ground Truth 형식으로 변환
    print("\n[3/3] Ground Truth 생성...")
    gt_dict = {}

    for r in successful:
        if r['overall_score'] >= 3:  # 3점 이상만 유사한 것으로 간주
            item_a_id = r['item_a_id']
            item_b_id = r['item_b_id']

            # A -> B
            if item_a_id not in gt_dict:
                gt_dict[item_a_id] = []
            gt_dict[item_a_id].append({
                'id': item_b_id,
                'concept_score': r['concept_score'],
                'image_score': r['image_score'],
                'solution_score': r['solution_score'],
                'overall_score': r['overall_score'],
                'reasoning': r['reasoning']
            })

            # B -> A (양방향)
            if item_b_id not in gt_dict:
                gt_dict[item_b_id] = []
            gt_dict[item_b_id].append({
                'id': item_a_id,
                'concept_score': r['concept_score'],
                'image_score': r['image_score'],
                'solution_score': r['solution_score'],
                'overall_score': r['overall_score'],
                'reasoning': r['reasoning']
            })

    # GT 포맷으로 변환
    ground_truth = []
    for query_id, relevant_items in gt_dict.items():
        ground_truth.append({
            'query_id': query_id,
            'query_category': 'image',
            'relevant_items': relevant_items
        })

    # 저장
    output_data = {
        'metadata': {
            'generation_method': 'GPT-4o with images',
            'model': 'gpt-4o',
            'total_pairs_evaluated': len(pairs),
            'successful_evaluations': len(successful),
            'failed_evaluations': len(failed),
            'min_relevance_score': 3,
            'total_queries': len(ground_truth),
            'total_relevant_pairs': sum(len(q['relevant_items']) for q in ground_truth) // 2,
            'cost': {
                'prompt_tokens': total_prompt if successful else 0,
                'completion_tokens': total_completion if successful else 0,
                'estimated_cost_usd': actual_cost if successful else 0
            }
        },
        'ground_truth': ground_truth,
        'raw_results': results  # 디버깅용
    }

    output_file = DATA_DIR / "ground_truth_image.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"      저장: {output_file}")
    print(f"      쿼리 수: {len(ground_truth)}")
    print(f"      유사 쌍 수: {sum(len(q['relevant_items']) for q in ground_truth) // 2}")

    # 실패 로그 저장
    if failed:
        error_file = DATA_DIR / "image_gt_errors.json"
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        print(f"      에러 로그: {error_file}")

    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
