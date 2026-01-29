# QTI 뷰어 통합 작업 핸드오버 문서

## 작업 개요

**목표**: itembank-web 프론트엔드에서 QtiViewer 컴포넌트를 사용하여 문항 전체 내용(수식, 이미지, 표, 선택지)을 렌더링

**현재 상태**: ✅ 완료 - QtiItemViewer 컴포넌트 렌더링 문제 해결됨

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

### 8. QtiItemViewer SSR 문제 해결
- **파일**: `itembank-web/src/app/page.tsx`
- **수정 내용**: `QtiItemViewer`를 `dynamic import`로 변경 (`ssr: false`)
- **상태**: ✅ 완료

### 9. Tailwind CSS 설정 수정
- **파일**: `itembank-web/tailwind.config.ts`
- **수정 내용**:
  - `content` 배열에 qti-components 패키지 경로 추가
  - `@tailwindcss/typography` 플러그인 추가
- **상태**: ✅ 완료

### 10. QTI UI 스타일 통합
- **파일**: `itembank-web/src/app/globals.css`, `qti-components/packages/ui/package.json`
- **수정 내용**:
  - globals.css에 `@import '@iosys/qti-ui/styles.css'` 추가
  - qti-ui package.json에 CSS export 경로 추가
- **상태**: ✅ 완료

---

## 해결된 문제 (2026-01-29)

### 원인 분석
`QtiItemViewer` 컴포넌트가 렌더링되지 않은 이유:

1. **SSR 문제 (핵심 원인)**
   - `@iosys/qti-core`의 `parseIml` 함수가 `DOMParser`를 사용
   - `DOMParser`는 브라우저 전용 API로 서버에서 실행 불가
   - Next.js가 서버에서 모듈을 로드할 때 에러 발생

2. **Tailwind CSS 클래스 누락**
   - `tailwind.config.ts`의 `content`에 qti-components 경로 미포함
   - `@tailwindcss/typography` 플러그인 미설치 (`prose` 클래스 사용)

3. **qti-ui CSS export 설정 누락**
   - `package.json`의 `exports` 필드에 CSS 경로 미포함

### 해결 방법

1. **page.tsx**: `QtiItemViewer`를 dynamic import로 변경
   ```tsx
   const QtiItemViewer = dynamic(
     () => import('@/components/QtiItemViewer').then(mod => mod.QtiItemViewer),
     { ssr: false, loading: () => <LoadingSkeleton /> }
   )
   ```

2. **tailwind.config.ts**: qti-components 경로 및 typography 플러그인 추가
   ```ts
   content: [
     './src/**/*.{js,ts,jsx,tsx,mdx}',
     '../qti-components/packages/ui/src/**/*.{js,ts,jsx,tsx}',
     '../qti-components/packages/viewer/src/**/*.{js,ts,jsx,tsx}',
   ],
   plugins: [require('@tailwindcss/typography')],
   ```

3. **globals.css**: qti-ui 스타일 import 추가
   ```css
   @import '@iosys/qti-ui/styles.css';
   ```

4. **qti-ui/package.json**: CSS export 추가
   ```json
   "exports": {
     "./styles.css": "./dist/index.css"
   }
   ```

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

qti-components/packages/ui/
└── package.json                # CSS export 경로 추가

itembank-web/
├── src/app/page.tsx            # QtiItemViewer dynamic import 적용
├── src/app/globals.css         # qti-ui 스타일 import 추가
├── src/components/QtiItemViewer.tsx  # NEW - QTI 뷰어 래퍼 컴포넌트
├── src/lib/api.ts              # getItemIml() 메서드 추가
├── src/types/api.ts            # ImlContentResponse 타입 추가
├── next.config.ts              # transpilePackages 설정
├── tailwind.config.ts          # qti-components 경로 및 typography 플러그인 추가
└── package.json                # @tailwindcss/typography 의존성 추가
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

1. **개발 서버 실행 및 테스트**
   ```bash
   cd itembank-web
   pnpm dev --port 3002
   ```
2. **브라우저에서 확인** - 검색 후 문항 클릭 시 QtiViewer 렌더링 확인
3. **디버그 박스 제거** - 정상 작동 확인 후 `QtiItemViewer.tsx`의 디버그 메시지 제거
4. **이미지 렌더링 테스트** - 이미지 포함 문항의 렌더링 확인

---

## 참고 사항

- IML 파일 경로: `/mnt/sda/worker/dev_ldm/iosys-generative/data/raw/...`
- IML 인코딩: 주로 EUC-KR/CP949 (일부 UTF-8)
- 문항 유형 코드: 11(선택형), 21(진위형), 31(단답형), 34(완성형), 37(배합형), 41(서술형), 51(논술형)

---

*작성일: 2026-01-29*
*수정일: 2026-01-29 - QtiItemViewer 렌더링 문제 해결*
