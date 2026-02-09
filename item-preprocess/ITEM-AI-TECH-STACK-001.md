# 기술 스택 문서

**문서 ID**: ITEM-AI-TECH-STACK-001
**버전**: v1.1.0
**대상 시스템**: 교육 문항 생성·검증·학습 자동화 Agent 플랫폼
**운영 방식**: 온프레미스 중심 멀티모델 협업 구조

---

## 1. 기술 전략

본 시스템은 다음 원칙을 따른다.

1. 모든 핵심 추론은 온프레미스에서 수행한다.
2. 이미지 이해는 전용 비전 모델을 통해 구조화 데이터로 변환한다.
3. 생성과 판정 모델은 역할을 분리하여 운영한다.
4. 모델 교체가 가능하도록 계층을 분리한다.
5. 학습 데이터는 내부에서 축적 및 재사용한다.

---

## 2. AI 모델 계층

| 계층                 | 역할        | 기술                   |
| ------------------ | --------- | -------------------- |
| Vision Parsing     | 이미지 구조화   | Qwen2.5-VL           |
| Intent Generation  | 문항 → 출제의도 | Local LLM            |
| Evaluation / Judge | 품질 판정     | Local LLM            |
| Item Generation    | 출제의도 → 문항 | Fine-tuned Local LLM |
| Embedding          | 검색/RAG    | Embedding Model      |

---

## 3. 모델 운영 역할 분리

### 3.1 Vision Model

* 입력: 문항 이미지
* 출력: 구조화 JSON (그래프/표/도형/텍스트)
* 사용 조건: Essential 이미지에서만 호출

### 3.2 Local LLM-A (Intent)

* 성취기준 후보 생성
* 성취수준 추정
* 출제의도 생성

### 3.3 Local LLM-B (Judge)

* 문항 품질 평가
* 정답 유일성 검증
* 거부사례 생성 근거 제공

### 3.4 Local LLM-C (Generator)

* 출제의도 기반 문항 생성
* JSON 스키마 준수 출력

---

## 4. 오케스트레이션 계층

| 구성          | 기술               |
| ----------- | ---------------- |
| Agent Flow  | LangChain (LCEL) |
| State Graph | LangGraph        |
| 비동기 작업      | Celery + Redis   |
| 스케줄링        | Airflow / Cron   |

---

## 5. 데이터 계층

| 저장소            | 역할           |
| -------------- | ------------ |
| Object Storage | QTI, 이미지     |
| Document DB    | 문항 및 결과 JSON |
| Vector DB      | RAG 검색       |
| Relational DB  | 메타데이터, 상태    |

---

## 6. 학습 인프라

| 구성        | 기술          |
| --------- | ----------- |
| Framework | PyTorch     |
| 튜닝        | LoRA / PEFT |
| 분산학습      | DeepSpeed   |
| 데이터셋      | JSONL       |
| 체크포인트     | Safetensors |

---

## 7. 추론 서빙

| 구성               | 기술      |
| ---------------- | ------- |
| Inference Engine | vLLM    |
| API              | FastAPI |
| Gateway          | Nginx   |
| 캐시               | Redis   |

---

## 8. 모니터링 및 실험관리

| 영역   | 도구         |
| ---- | ---------- |
| 로그   | ELK        |
| 메트릭  | Prometheus |
| 대시보드 | Grafana    |
| 실험관리 | MLflow     |

---

## 9. 배포 환경

| 환경       | 기술             |
| -------- | -------------- |
| 컨테이너     | Docker         |
| 오케스트레이션  | Kubernetes     |
| 모델 버전 관리 | Model Registry |

---

## 10. 보안 정책

* 외부 LLM 호출 금지
* 온프레미스 데이터 격리
* 접근 제어 기반 API 인증
* 학습 데이터 익명화

---

## 11. 구성 요약

본 시스템은 다음 구조를 따른다.

* Vision Model → 구조화 데이터 생성
* Intent Model → 출제의도 생성
* Generator Model → 문항 생성
* Judge Model → 품질 판정
* Trainer → 지속 학습

각 모델은 독립 서비스로 배포되며, 오케스트레이터가 흐름을 제어한다.

---

**끝**
