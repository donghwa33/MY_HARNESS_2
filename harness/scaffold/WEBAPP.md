# 웹 서비스 구조 기준

문제 풀이 + 웹 서비스 과제에서 따르는 기본 구조다. 과제가 다른 구조를 요구하면 과제를 따르고, 바꾼 이유를 DECISIONS 에 기록한다.

## 1. 기술 스택
| 층 | 선택 | 이유 |
|---|---|---|
| HTTP | FastAPI + Pydantic | 계층을 파일로 나누기 쉽고 입력 형식 검증이 내장 |
| DB | SQLite (표준 `sqlite3`, WAL) | 설치 없이 트랜잭션·외래 키 |
| 계산 | 순수 파이썬 모듈, 필요하면 OR-Tools | 웹·DB 없이 단독 테스트, 알고리즘 교체 |
| 화면 | 정적 HTML + fetch (+ Canvas/SVG) | 빌드 없이 동작, 서버 결과만 표시 |
| 실행 | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | 미리보기 도구 조건 |

## 2. 폴더
```
app/
  main.py      앱 조립, 시작 시 DB 초기화
  api.py       HTTP
  schemas.py   요청·응답 형식
  services.py  흐름
  repo.py      DB
  schema.sql   테이블
  core/        계산 (model.py, check.py, solve.py)
  static/      화면
tests/         test_core.py, test_api.py, test_boundaries.py
run.sh
```

## 3. 계층과 경계
| 층 | 하는 일 | 하지 않는 일 | import 금지 |
|---|---|---|---|
| api | 형식 검증, 권한, 서비스 호출, 오류 → 상태 코드 | 계산, SQL | sqlite3, app.repo, app.core |
| services | 트랜잭션, 입력 버전 저장, 실행 기록, 계산 호출, 결과 저장, 게시 | HTTP 객체, SQL | fastapi, sqlite3, app.api |
| repo | SQL | 계산, HTTP | fastapi, app.core, app.services, app.api |
| core | 계산, 조건 검증 | 웹, DB | fastapi, sqlite3, app.repo, app.services, app.api |

`tests/test_boundaries.py`: 각 파일을 `ast` 로 파싱해 import 를 모으고(`from . import x` 는 `app.x` 로), 위 금지 목록과 겹치면 실패시킨다.

## 4. 데이터 흐름

### 입력을 바꿀 때
1. api: 형식 검증(실패 422), 권한 확인(실패 403)
2. services: 트랜잭션으로 입력을 **새 버전**으로 저장 (기존 버전은 수정하지 않음)
3. services: 쓰기 잠금 안에서 진행 중인 실행이 있으면 거절(409), 없으면 실행을 `running` 으로 기록
4. core: 계산 (트랜잭션 밖, 시간 제한) → 검증기로 조건 확인
5. services: 결과에 따라 한 트랜잭션으로
   - 성공: 결과 저장 + `succeeded` + 게시 교체
   - 조건 충돌: `infeasible` + 원인 기록, 게시 유지
   - 오류: `failed` + 오류 기록, 게시 유지
6. api: 실행 상태와 원인을 응답 (불가능·실패도 200 + status)

### 결과를 볼 때
services 가 게시된 실행의 결과만 읽는다. 없으면 404 와 안내 문구.

## 5. DB

### 공통 테이블
```sql
CREATE TABLE datasets (id INTEGER PRIMARY KEY, created_at TEXT, created_by TEXT,
                       input_hash TEXT, payload TEXT);              -- 입력 버전, 불변
CREATE TABLE runs (id INTEGER PRIMARY KEY, dataset_id INTEGER REFERENCES datasets(id),
                   algorithm TEXT, params TEXT,
                   status TEXT CHECK (status IN ('running','succeeded','infeasible','failed')),
                   started_at TEXT, finished_at TEXT, score REAL, solver_status TEXT, reason TEXT);
CREATE TABLE results (run_id INTEGER REFERENCES runs(id), seq INTEGER, payload TEXT,
                      PRIMARY KEY (run_id, seq));
CREATE TABLE published (id INTEGER PRIMARY KEY CHECK (id = 1), run_id INTEGER REFERENCES runs(id),
                        published_at TEXT);                         -- 사용자가 보는 결과 하나
```
- 도메인 테이블은 `dataset_id`(입력) 또는 `run_id`(결과) 외래 키로 붙인다.
- 계산에 통째로 쓰는 입력은 JSON 으로, 화면에서 조회·집계하는 결과는 테이블로.

### 연결과 트랜잭션
- 요청마다 새 연결. 연결을 전역이나 스레드 사이에 공유하지 않는다.
- `PRAGMA journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`.
- 쓰기는 `BEGIN IMMEDIATE ... COMMIT`, 예외 시 `ROLLBACK`.
- 계산은 트랜잭션 밖에서 한다.
- 앱 시작 시 `running` 으로 남은 실행을 `failed (interrupted)` 로 정리한다.

## 6. core

### 인터페이스
```python
@dataclass(frozen=True)
class Problem: ...            # 입력, 조건, 인자(가중치·시간 제한·시드)
@dataclass
class Solution: ...           # 선택 결과, 알고리즘 이름, 걸린 시간, solver_status
@dataclass
class Evaluation: ...         # feasible, violations: list[str], score
class Infeasible(Exception):  # reasons: 조건 충돌 원인
    ...

def evaluate(problem, solution) -> Evaluation     # 검증기. 알고리즘과 독립
def solve(problem, algorithm) -> Solution          # SOLVERS 에 등록된 알고리즘 실행
def compare(problem, algorithms) -> list[dict]     # 위반 → 점수 → 시간 순 비교표
```

### 규칙
- 반드시 지킬 조건은 검증기가 세고, 위반이 있으면 게시하지 않는다. 점수는 목적값으로만 쓴다.
- 조건을 어길 수밖에 없는 후보는 선택 전에 제거한다. 그 뒤 필수 항목을 충족할 후보가 없으면 계산 전에 `Infeasible` 과 원인을 낸다.
- 같은 입력이면 같은 결과: 정렬·동점 기준 고정, 솔버 시드 고정, `num_workers=1`.
- 입력의 일부에만 의존하는 무거운 계산(거리 행렬, 가시성 표 등)은 그 부분의 해시로 캐시한다.

## 7. 알고리즘 예시

기본 전략: **탐욕(기준선) → OR-Tools(주력, 시간 제한) → 같은 입력 세트로 비교**. OR-Tools 가 설치되지 않으면 탐욕 + 국소 탐색.

## 8. API 예시
| 경로 | 권한 | 응답 |
|---|---|---|
| `POST /api/datasets` | 관리 | 201 + 버전 id |
| `POST /api/runs` | 관리 | 실행 상태 (succeeded / infeasible / failed + 원인), 진행 중이면 409 |
| `GET /api/runs/{id}` | 누구나 | 실행 상태 |
| `GET /api/result` | 누구나 | 게시된 결과, 없으면 404 |
| `GET /` | 누구나 | 화면 |

권한이 필요하면 FastAPI `Depends` 로 한 곳에서 검사한다.

## 9. 화면
- 서버가 준 결과만 그린다. 계산하지 않는다.
- 값은 `textContent` 로만 넣는다.
- 상태를 구분해 보여준다: 계산 중 / 성공 / 불가능(원인) / 실패(오류).
- 결과가 어떤 입력 버전·실행에서 나왔는지 표시한다.

## 10. 테스트 (최소)
| 테스트 | 확인 |
|---|---|
| test_core | 검증기를 손으로 답을 아는 예제로, 모든 알고리즘 결과가 검증기를 통과, 같은 입력 같은 결과 |
| test_api | 입력 → 계산 → 결과 조회 전체 흐름 (FastAPI TestClient, 임시 DB) |
| test_api | 실패·불가능 때 게시된 결과가 그대로인지 |
| test_api | 진행 중인 실행이 있으면 409 |
| test_api | 권한 없음 403, 잘못된 형식 422 |
| test_boundaries | 3절 import 금지 |
