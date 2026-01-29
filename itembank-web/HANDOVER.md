# QTI 뷰어 통합 작업 핸드오버 문서

## 작업 개요

**목표**: itembank-web 프론트엔드에서 QtiViewer 컴포넌트를 사용하여 문항 전체 내용(수식, 이미지, 표, 선택지)을 렌더링

**현재 상태**: ❌ 미완료 - QtiItemViewer 컴포넌트가 상세 패널에서 렌더링되지 않음

---

## 아키텍처

```
[Frontend: itembank-web (Next.js)]
    ↓ API 호출
[Backend: itembank-api (FastAPI)]
    ↓ IML 파일 읽기
[IML Files: /mnt/sda/worker/dev_ldm/iosys-generative/data/raw/...]

프론트엔드 흐름:
1. QtiItemViewer → api.getItemIml(itemId) 호출
2. IML XML 수신
3. parseIml() → ImlItem 객체 생성
4. imlToQti() → AssessmentItem 객체 생성
5. QtiViewer → 렌더링
```

---

## 완료된 작업

### 1. Backend API 엔드포인트 추가
- **파일**: `itembank-api/api/routers/search.py`
- **엔드포인트**: `GET /search/items/{item_id}/iml`
- **기능**: item_id로 DB 조회 → source_file 경로 → IML 파일 읽기 → XML 반환
- **테스트**: ✅ 정상 작동
```bash
curl http://localhost:8000/search/items/{ITEM_ID}/iml
# 200 OK, IML XML 반환됨
```

### 2. IML 파일 리더 유틸리티
- **파일**: `itembank-api/utils/iml_reader.py`
- **기능**: EUC-KR/CP949/UTF-8 인코딩 자동 감지 및 읽기

### 3. IML 파서 수정
- **파일**: `qti-components/packages/core/src/parser/iml-parser.ts`
- **수정 내용**:
  - `parseParagraph()`: `<문자열>`, `<수식>`, `<그림>` 혼합 콘텐츠 처리
  - `parseBlockContent()`: `<보기>` 요소 처리 추가
  - `findItemElement()`: `<문항종류>` → `<단위문항>` → `<문항>` 구조 탐색

### 4. IML to QTI 변환기 수정
- **파일**: `qti-components/packages/core/src/parser/iml-to-qti.ts`
- **수정 내용**: `paragraphToHtml()`에서 수식/이미지 혼합 콘텐츠 HTML 변환

### 5. 프론트엔드 타입 및 API 클라이언트
- **파일**: `itembank-web/src/types/api.ts`
  - `choices` 필드 추가
- **파일**: `itembank-web/src/lib/api.ts`
  - `getItemIml()` 메서드 추가
  - `normalizeSearchResponse()`에 choices 파싱 추가

### 6. QtiItemViewer 컴포넌트
- **파일**: `itembank-web/src/components/QtiItemViewer.tsx`
- **기능**:
  - IML API 호출 (react-query 사용)
  - parseIml() → imlToQti() 변환
  - QtiViewer 렌더링
  - 에러 상태 표시 (API Error, Parse Error, No Data)
- **fallback 제거됨**: MathText fallback 없음

### 7. 검색 결과 목록 선택지 표시
- **파일**: `itembank-web/src/app/page.tsx`
- **ItemCard 컴포넌트**: choices 필드 표시 추가 (①②③... 형식)
- **상태**: ✅ 정상 작동 - 검색 결과에 선택지 표시됨

---

## 미완료 작업 (핵심 문제)

### 문제 설명
`page.tsx`의 `ItemDetailView` 컴포넌트에서 `QtiItemViewer`를 사용하도록 코드가 작성되어 있으나, 실제 브라우저에서는 QtiItemViewer가 렌더링되지 않음.

**예상 동작**:
- 검색 결과 클릭 → 오른쪽 상세 패널에 QtiItemViewer 렌더링
- 파란 박스 "✓ QtiViewer 적용됨" 표시 (디버그용)

**실제 동작**:
- QtiItemViewer가 렌더링되지 않음
- 원인 불명

### 디버깅을 위해 확인할 사항

1. **브라우저 콘솔 에러 확인** (F12 → Console)
   - React 에러?
   - Import 에러?
   - Runtime 에러?

2. **네트워크 요청 확인** (F12 → Network)
   - `/api/search/items/{id}/iml` 요청이 발생하는가?
   - 응답 상태 코드는?

3. **React DevTools 확인**
   - QtiItemViewer 컴포넌트가 트리에 존재하는가?
   - props가 제대로 전달되는가?

4. **컴포넌트 렌더링 상태 확인**
   - Loading? Error? Success?
   - QtiItemViewer.tsx의 각 return 문에 console.log 추가하여 확인

### 의심되는 원인

1. **@iosys/qti-core, @iosys/qti-viewer import 실패**
   - pnpm workspace 링크 문제?
   - 빌드 누락?

2. **React Query 설정 문제**
   - QueryClientProvider가 제대로 설정되어 있는가?

3. **브라우저 캐시**
   - 강제 새로고침 (Ctrl+Shift+R) 필요

4. **SSR/CSR 문제**
   - 'use client' 지시문 확인
   - 서버 사이드에서 실행되는 코드가 있는가?

---

## 관련 파일 목록

### 수정된 파일
```
itembank-api/
├── api/core/config.py          # iml_data_path 설정 추가
├── api/models/schemas.py       # ImlContentResponse 스키마 추가
├── api/routers/search.py       # /items/{id}/iml 엔드포인트 추가
└── utils/iml_reader.py         # NEW - IML 파일 리더

qti-components/packages/core/src/parser/
├── iml-parser.ts               # IML 파싱 로직 수정
└── iml-to-qti.ts               # QTI 변환 로직 수정

itembank-web/
├── src/app/page.tsx            # ItemDetailView에 QtiItemViewer 사용
├── src/components/QtiItemViewer.tsx  # NEW - QTI 뷰어 래퍼 컴포넌트
├── src/lib/api.ts              # getItemIml() 메서드 추가
├── src/types/api.ts            # ImlContentResponse 타입 추가
└── next.config.ts              # transpilePackages 설정
```

### 빌드 명령어
```bash
# qti-components 패키지 빌드
cd /mnt/sda/worker/dev_ldm/iosys-generative
pnpm -F @iosys/qti-core build
pnpm -F @iosys/qti-viewer build

# 프론트엔드 개발 서버
cd itembank-web
rm -rf .next node_modules/.cache
pnpm dev --port 3002

# API 서버 (별도 터미널)
cd itembank-api
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 서비스 접속 정보

- **Frontend**: http://localhost:3002
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5433 (Docker: poc-pgvector)

---

## 다음 단계 제안

1. **브라우저 콘솔 에러 확인** - 가장 먼저 확인
2. **QtiItemViewer에 console.log 추가**하여 어느 상태에서 멈추는지 확인
3. **@iosys/qti-core import 테스트** - 별도 테스트 파일로 확인
4. **React Query 동작 확인** - useQuery가 실행되는지 확인
5. **단순화된 테스트** - QtiItemViewer 대신 단순 텍스트만 렌더링하여 컴포넌트 자체가 렌더링되는지 확인

---

## 참고 사항

- IML 파일 경로: `/mnt/sda/worker/dev_ldm/iosys-generative/data/raw/...`
- IML 인코딩: 주로 EUC-KR/CP949 (일부 UTF-8)
- 문항 유형 코드: 11(선택형), 21(진위형), 31(단답형), 34(완성형), 37(배합형), 41(서술형), 51(논술형)

---

*작성일: 2026-01-29*
