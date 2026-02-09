📌 요약: 최신 기술 동향 (Version 기반)

✅ 최신 공개 모델과 Agentic Vision
	•	공식적으로 Agentic Vision 기능은 Gemini 3 Flash에서 새롭게 도입된 기술입니다. 2026년 1월 27일 Google 블로그를 통해 공개되었으며, 시각적 판단을 위해 코드 실행(visual code + reasoning) 기능을 결합한 것이 핵심입니다.  ￼
	•	Gemini 1.5 Flash는 Agentic Vision이 공식적으로 제공되는 버전이 아닙니다. 오히려 2024년 공개된 1.5 Flash는 프로덕션 중심의 경량 모델로 지원만 확인되며 Agentic Vision 언급은 없습니다.  ￼

👉 따라서 백서에서 “Gemini 1.5 Flash의 Agentic Vision”이라고 명시한 부분은 버전 오기재이며, 현재 공식적으로는 Gemini 3 Flash에서만 지원됩니다.

⸻

🧠 Agentic Vision: 기술 원리 (공식 및 최신)

✅ 기술 정의 (공식)

Agentic Vision = 시각적 추론 + 실행 가능한 코드 생성 및 수행

Google 발표 요약:
	1.	Think (계획)
사용자 입력 + 이미지 분석 → 세부 추정 필요 여부 판단
→ 이 과정을 거쳐 “여기 확대가 필요하다” 등 계획을 수립함.  ￼
	2.	Act (행동)
생성된 계획을 코드로 변환 → Python으로 이미지 처리 (crop/rotate/annotate 등)
→ 이 과정은 금전적 계산/visual graph 생성까지 확장 가능.  ￼
	3.	Observe (관찰)
실행 결과를 context window에 다시 넣어 모델이 재추론
→ 최종 답변 생성.  ￼

자체적으로 이미지를 단 한 번 스캔하는 기존 비전과 달리,
시각 데이터를 ‘능동적 탐색(Active Investigation)’ 과정으로 처리합니다.  ￼

🔍 작동 목적
	•	단순 객체 식별을 넘어서 세부 정보나 도면·작은 문자를 놓치지 않고 추론
→ 예: 건축 설계도의 작은 치수값 읽기, 이미지 기반 수치 계산, bounding box annotation.  ￼

⸻

📊 성능 개선: 벤치마크 데이터

공식 데이터 기반

Google 공식 발표에 따르면, Agentic Vision 활성화 시 코드 실행 도구를 켜면 대부분 비전 벤치마크에서 약
➡️ 5~10% 품질 향상이 관측됨.  ￼
	•	이 수치는 *Office QA 65→70%*와 같은 특정 예시보다는 전반적 비전 작업 품질 개선 지표로 해석하는 것이 좋습니다.
	•	즉, WordQA/VisualQnA/숫자 읽기/멀티스케일 객체 인식 등에서 전형적인 범위입니다.  ￼

⸻

🧪 구현 방법론(현재 기준)

1) Google AI Studio
	•	Agentic Vision 기능은 AI Studio에서 코드 실행 활성화로 동작
→ Python code execution 활성화가 중요.  ￼
	•	사용 예시
→ 이미지 업로드 + “Zoom in if needed” 형태의 prompt와 함께 실행
→ 모델이 자동으로 Think → Act → Observe 프로세스를 보여줌.  ￼
	•	Thought visualization (사고 과정) 기능으로 Debug/Prompt engineering 지원.

2) Python API (Gemini API)

공식 자료에서는 Gemini 3 Flash 기준 코드 실행 예시가 공개되어 있습니다.

Python 예시 (공식 구조):

from google.ai import genai

model = genai.GenerativeModel(
    model_name="models/gemini-3-flash-preview",
    tools=["code_execution"]
)

response = model.generate_content([
    "zoom into the required area and analyze",
    image
])
print(response.text)

✍️ 핵심:
✔ tools=["code_execution"] 옵션이 Agentic Vision 기능의 활성화 토글 역할을 합니다.  ￼

⸻

🆚 Gemini 1.5 Flash vs Gemini 3 Flash

항목	Gemini 1.5 Flash	Gemini 3 Flash (Agentic Vision)
Agentic Vision	❌ 공식 지원 없음	✅ 공식 도입  ￼
Code Execution	일부 가능 (예전 수준)	도구형 Python 코드 기반 실행  ￼
벤치마크 향상	일반 비전 수준	5~10% Vision 품질 개선  ￼
Vision 조사	정적 한 번 분석	Think+Act+Observe 동적 분석  ￼

👉 백서가 “Gemini 1.5 Flash에 Agentic Vision을 갖는다”로 작성되어 있던 부분은 현시점 기준 최신 업데이트와 일치하지 않습니다.
실제로 공식 문서는 Gemini 3 Flash에서 최초 발표된 기능임을 반영해야 합니다.

⸻

📌 결론

✔ Agentic Vision 기술은 현재 Gemini 3 Flash에 공식으로 도입된 기술입니다.  ￼
✔ 성능 향상은 대체로 5~10% 범위에서 관측되며, 일반 Vision task에서 유의미한 정밀도 개선을 제공합니다.  ￼
✔ Think-Act-Observe 루프 방식은 공식 문서에서 반복 설명되며, 동적 이미지 조작 기반의 시각 분해능 향상을 설계 의도로 하고 있습니다.  ￼

⸻

📌 수정 권장 사항(백서 방향)

1. 버전 업데이트
→ “Gemini 1.5 Flash의 Agentic Vision” → “Gemini 3 Flash Agentic Vision” 으로 수정 필요.

2. 벤치마크 인용
→ 공식 공개 기준으로 5~10% 개선 폭 사용: Office QA 같은 임의 지표가 아닌 보편적 개선 표기 권장.

3. 구현 코드 예시
→ Python API 예제는 예시 그대로 Gemini 3 Flash 중심으로 업데이트 필요.

4. 발표 시기 명시
→ 2026년 1월 27일 Google 공식 기술 블로그를 근거로 기능 발표(공식 일정) 명시.
