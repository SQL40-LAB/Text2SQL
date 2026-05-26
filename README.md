# Text2SQL

자연어로 설명한 쿼리 요청을 바탕으로, 데이터베이스 스키마 정보를 필터링한 뒤 ChatGPT API로 SQL을 생성하고 검증해 반환하는 Python 서비스입니다.

## 아키텍처 개요

```
사용자(UI) → Python 서버 → [스키마 로드] → 키워드 필터링 → 프롬프트 생성
    → ChatGPT API → SQL 파서 검증 → SQL 반환
```

- **스키마 저장소**: 운영 시 GitHub YAML을 사용하도록 설계되어 있으며, 현재는 `data/schemas/` 아래 **임시 YAML 3종**을 사용합니다.
- **DB 직접 연결 없음**: 스키마 정의만 사용하며 실제 DB에 접속하지 않습니다.
- **키워드 필터링 필수**: DB 단위가 아니라 **관련 테이블·컬럼만** 골라 압축 형식으로 프롬프트에 넣어 토큰을 최소화합니다.
- **동의어(aliases)**: 각 YAML의 DB·테이블·컬럼에 `aliases` 목록을 정의하면, 질의 키워드와 매칭합니다 (코드 내 하드코딩 맵 없음).

## 프로젝트 구조

```
T-Lab/
├── app.py                 # Streamlit UI
├── requirements.txt
├── .env.example
├── data/schemas/          # 임시 스키마 YAML
│   ├── ecommerce.yaml     # 전자상거래
│   ├── hr.yaml            # 인사/급여
│   └── analytics.yaml     # 마케팅/로그 분석
└── src/
    ├── config.py          # 설정
    ├── schema_loader.py   # 스키마 로드
    ├── keyword_filter.py  # 키워드 필터링
    ├── prompt_builder.py  # 프롬프트 생성
    ├── openai_client.py   # ChatGPT API
    ├── sql_validator.py   # SQL 파서 검증
    └── pipeline.py        # 전체 파이프라인
```

## 설치 및 실행

### 1. 가상 환경 (권장)

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. 환경 변수

`.env.example`을 복사해 `.env`를 만들고 OpenAI API 키를 설정합니다.

```bash
copy .env.example .env
```

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

API 키 없이 UI·필터링만 테스트하려면 앱 실행 후 사이드바에서 **「모의 모드」**를 켜세요.

### 3. 앱 실행

```bash
streamlit run app.py
```

브라우저에서 입력창에 자연어 질의를 입력한 뒤 **SQL 생성**을 누르면 됩니다.

## 사용 예시

| 질의 예시 | 관련 스키마 |
|-----------|-------------|
| 부서별 직원 수와 평균 연봉 | hr |
| 배송 완료된 주문의 총 매출 | ecommerce |
| 캠페인별 전환 수와 매출 | analytics |

## 처리 단계 (흐름도 대응)

1. **질의**: 사용자가 UI에 자연어 입력
2. **스키마 로드**: 로컬 YAML 3개 로드 (향후 GitHub API로 교체 가능)
3. **키워드 필터링**: 질의와 매칭되는 테이블·컬럼만 추출
4. **프롬프트 생성**: 필터링된 스키마 + 질의
5. **ChatGPT API**: SQL 생성
6. **SQL 파서 검증**: `sqlglot`으로 구문 검증 및 포맷
7. **결과 반환**: UI에 SQL 및 중간 결과 표시

## 스키마 YAML — aliases 작성법

테이블·컬럼 추가 시 검색용 한국어/영문 키워드를 함께 적습니다.

```yaml
tables:
  - name: employees
    description: 직원 마스터
    aliases: [직원, 사원, employee, employees]
    columns:
      - name: salary
        description: 기본 연봉
        aliases: [연봉, 급여, 임금]
```

필터는 `name`, `description`, `aliases`로 관련 **테이블·컬럼만** 고릅니다. ChatGPT에는 aliases 없이 압축 한 줄 형식으로 전달합니다.

```
hr.employees(emp_id INTEGER PK, dept_id INTEGER FK->departments.dept_id, salary DECIMAL)
```

## GitHub 스키마 연동 (향후)

`src/schema_loader.py`의 `load_all_schemas()`를 GitHub Contents API 호출로 교체하면 동일 파이프라인을 유지한 채 원격 YAML을 사용할 수 있습니다.

## 기술 스택

- Python 3.9+
- Streamlit (UI)
- OpenAI API (SQL 생성)
- PyYAML (스키마)
- sqlglot (SQL 검증)

## 주의사항

- 생성된 SQL은 참고용이며, 실행 전 반드시 검토하세요.
- n8n 등 외부 워크플로 도구는 사용하지 않습니다.
- 실제 DB 연결·쿼리 실행 기능은 포함하지 않습니다.
