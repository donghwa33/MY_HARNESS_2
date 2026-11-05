# 03. S2 정제

스킬: harness/skills/decision-log/SKILL.md

## 1. 정제 후보 목록
```
$decision-log AGENTS.md 5절을 따른다. outputs/inventory.md 를 바탕으로 정제가 필요한 항목을 outputs/profile.md 에 표로 정리하라.
열: 파일·열 / 문제 유형(포맷 혼재·표기 혼재·중복·범위 이탈·조인 실패·결측) / 영향 행 수와 예시 / 확실성(확정·판단·미정) / 추천 처리 / 이유(데이터 근거) / 대안과 그 대안이 맞는 조건(판단 항목만).
확정 항목은 대안을 만들지 말고 근거만 써라. 미정 항목은 요청자에게 물을 질문을 써라.
날짜 슬래시 포맷이 있으면 infer_slash_order() 결과를 근거로 써라. 처리는 하지 말고 내 결정을 기다려라.
```

## 2. 자주 나오는 함정과 기본 결정 (대부분 '확정', 재측정 기준만 보통 '판단')
| 함정 | 기본 결정 | 확인 |
|---|---|---|
| 범주 표기 혼재 | normalize_categories 명시 매핑, 미등록 값은 에러 | 매핑 단위 테스트 |
| 날짜 포맷 혼재 | parse_dates_strict 허용 포맷 목록. 슬래시는 infer_slash_order 근거로 판정 | 파싱 후 기간 범위 검사 |
| 재측정·중복 행 | dedupe_keep (기준은 요청자의 업무 정의) + 반대 기준을 민감도로 | 키 유일성 테스트 |
| 범위 이탈 | isolate_out_of_range 로 격리, 개수 보고 | 범위 테스트 |
| 조인 실패 | join_report 로 손실 키 격리, 비율 보고 | 손실 키 격리 테스트 |

## 3. 결정 기록
```
$decision-log 확정 항목은 추천대로 승인한다 (하나의 D-번호로 묶어도 된다).
판단 항목은 다음과 같이 결정한다: (예: <항목1> 은 추천대로. <항목2> 는 대안 (b), 이유: INTERVIEW #<번호>. 추천안은 민감도 분석으로)
work/DECISIONS.md 에 기록하라.
```

## 4. 구현과 테스트
```
work/DECISIONS.md 의 결정을 구현하는 src/clean.py 를 작성하라.
- analysis_utils 의 정제 함수를 쓰고, 결정마다 함수 하나, docstring 첫 줄에 D-번호.
- main(): data/raw → data/clean/<이름>_clean.csv, 단계별 행 수 변화 outputs/tables/cleaning_summary.csv, 격리 파일들.
- tests/test_clean.py 에 결정별 단위 테스트, tests/test_invariants.py 에 harness/scaffold/test_invariants_template.py 를 열 이름에 맞게 수정.
python -m pytest 실행. 실패하면 코드를 고치고, 테스트를 고쳐야 한다면 먼저 이유를 말하라.
```

## 5. 마무리
- 커밋: `[S2] D-001~D-00x 정제`
- EXPLAIN: 결과 영향이 큰 결정이 있으면 추가
- STATE 갱신 → `$handoff` (07)
