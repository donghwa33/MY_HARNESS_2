# MY_HARNESS

AI 코딩 에이전트(Codex 등 AGENTS.md·Agent Skills 를 지원하는 도구)와 함께 데이터 분석·문제 해결 작업을 할 때 쓰는 범용 작업 하네스입니다.
분석 스캐폴드는 제조·품질 데이터에 맞춰져 있지만, 규칙과 스킬은 다른 작업에도 씁니다. 설치 후 이 문서는 `harness/README.md` 로도 열 수 있습니다.

---

## 1. 설치 (작업 공간 루트에서)

```bash
git clone https://github.com/donghwa33/MY_HARNESS .kit && bash .kit/bootstrap.sh
codex
```
- 홈 디렉터리가 아닌 전용 작업 폴더의 루트에서 실행합니다. 설치가 끝나면 `.kit` 는 지워집니다. 작업 공간에 원래 있던 파일(README, AGENTS.md 등)은 덮어쓰지 않습니다.
- 스킬 6개를 `.agents/skills` 에 연결해 Codex 에서 `/skills`, `$이름` 으로 쓸 수 있게 합니다.
- 옵션: `--ws <경로>`, `--user-skills`, `--no-repo-skills`, `--no-install`

### 시작 직후 확인 3가지
1. `시작` → 첫 줄 `[harness loaded]`
2. `/skills` → interview, decision-log, stratify-analysis, redteam, handoff, explain-pack
3. `/status`, `/model` → 모델 확인

---

## 2. 원칙

1. 스킬은 `$이름` 으로 부른다.
2. 지시 끝에 멈출 지점을 쓴다: `… 하고 멈춰라`
3. 질문인지 작업인지 밝힌다: `기존 결과로 답만 해` / `분석해서 FINDINGS 에 기록해`.
4. 제안은 확실성·추천·이유로 받고, 확정 항목은 한 번에 승인한다.
5. 숫자는 스크립트로 계산해 outputs/ 에 저장하고 출처를 달게 한다.
6. 요청자에게 보낼 메시지는 초안만 받고 직접 보낸다.
7. Codex 가 작업하는 동안 다른 일을 하되 승인 대기를 확인한다. 같은 파일을 에디터에서 동시에 고치지 않는다.
8. `/compact` 대신 `$handoff` → `/new`.

---

### 위임 프롬프트 틀
코드·분석을 맡길 때는 이 형식으로 준다. 범위와 완료 기준을 사람이 정했다는 것이 기록에 남는다.
```
목표: <이번에 할 일 하나>
입력·출력: <함수 형식이나 파일>
조건: <반드시 지킬 것 / 점수로 볼 것>
하지 마라: <건드리면 안 되는 파일·층, 범위 밖 기능>
완료 조건: <통과해야 할 테스트 이름 또는 확인 방법>
끝나면: <보고할 것>. 멈춰라.
```

## 3. 단계별 프롬프트

### S0 셋업
```
시작
```
```
원본 데이터를 data/raw/ 로 복사하라. analysis_utils.profile() 로 요약하는 src/inventory.py 를 만들어 outputs/inventory.md 에 저장하라.
분석은 하지 말고, 파일별 기간·행 수, 날짜·설비·자재·측정 관련 열, 이상해 보이는 값의 종류만 요약하고 멈춰라.
```

### S1 인터뷰와 합의
```
$interview 아래 대화 원문으로 work/INTERVIEW.md 를 작성하고 멈춰라.
(대화 원문)
```
```
$interview AGREEMENT 초안과 요청자 확인 메시지(5줄 이내)를 써라. 요청자의 가설은 검증 대상으로 둬라.
```

### S2 정제
```
$decision-log outputs/inventory.md 기준으로 정제 항목을 표로 제안하고 내 결정을 기다려라.
```
```
$decision-log 확정 항목은 추천대로 승인. 판단 항목: <항목> 은 <선택>, 이유 <근거>.
기록하고 src/clean.py 와 테스트를 구현해 실행하라. 끝나면 [S2] 로 커밋하고 멈춰라.
```

### S3 분석
```
$stratify-analysis 가설 <A>, <B> 를 같은 층화표에서 비교하라. 기간 <이후>, 값 <지표>, 단위 <Lot>.
결과를 FINDINGS 에 F-번호로 쓰고 멈춰라.
```
세부 순서는 `harness/playbook/04_S3_analysis.md`.

### S4 검증
```
$redteam 결론 "<핵심 결론 한 문장>" 을 검토하라.
```
별도 세션으로 하려면 새 터미널에서 `codex` 를 실행하고 같은 프롬프트를 쓴다.

### S5 산출
```
요구사항의 지정 파일 <파일명들> 을 work/ 문서를 바탕으로 작성하라. 숫자는 출처를 괄호로 달아라.
깨끗한 상태에서 재현 명령을 실행해 확인하고 [S5] 로 커밋하라.
```

### 인계
```
$handoff
```
`/new` 후:
```
work/HANDOFF.md 만 읽어라. 다른 파일은 다음 행동에 필요할 때 그 부분만 읽어라.
세 줄만 답하라: 1) 다음 행동 2) 유효 결정 번호 3) 열린 질문
```

### 마감
```
$explain-pack
```

---

## 4. 짧은 지시

| 상황 | 지시 |
|---|---|
| 답만 필요 | `기존 outputs/ 로 답만 해. 코드·문서·커밋은 만들지 마.` |
| 기록까지 필요 | `분석해서 FINDINGS 에 기록하고 멈춰라.` |
| 앞서 나감 | `멈춰라. 한 것과 바뀐 파일만 요약하라.` |
| 추천이 없음 | `확실성, 추천, 이유부터 다시.` |
| 답이 명확한데 대안을 만듦 | `확정 항목이다. 근거와 추천만.` |
| 숫자 출처가 없음 | `이 숫자를 계산한 파일과 함수를 달아라.` |
| 범위 밖 | `범위 밖이다. 제안만 남겨라.` |
| 결정 변경 | `D-0xx 를 D-0yy 로 대체하고 STATE 유효 결정을 고쳐라.` |
| 결과가 틀림 | `잘못됐다: <무엇이 왜>. 고치고 기록하라.` |
| 커밋 | `지금까지 변경을 [S단계] 로 한 번에 커밋하라.` |

---

## 5. 구성

| 경로 | 내용 |
|---|---|
| AGENTS.md | 작업 규칙 (작업 공간 루트로 복사) |
| harness/skills/ | interview, decision-log, stratify-analysis, redteam, handoff, explain-pack |
| harness/templates/ | STATE, INTERVIEW, AGREEMENT, DECISIONS, FINDINGS, EXPLAIN, REVIEW, HANDOFF, REPORT, ACTIONS, README_RUN |
| harness/scaffold/ | analysis_utils.py (+테스트), 테스트·재현 템플릿, 웹 서비스 구조 기준 WEBAPP.md (스택·계층·DB·흐름·OR-Tools 예시) |
| harness/playbook/ | 단계별 절차 (00_flow ~ 08_closing_and_review_prep) |
