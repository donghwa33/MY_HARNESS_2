# 06. S5 산출물

## 1. 지정 파일 매핑
요구사항이 지정한 파일명을 기준으로 work/ 문서의 내용을 어디에 담을지 정한다.
| 요구 산출물 (예) | 담을 내용 (출처) |
|---|---|
| 계획 문서 | AGREEMENT + 단계 구성 + 결정 요지 |
| 협업·작업 기록 | INTERVIEW 요약, DECISIONS, REVIEW 판정, AI 제안 수용/기각 |
| 결과 보고 | REPORT 템플릿 구조 |
| 도구·화면 | app/ + run.sh + README_RUN |
지정이 없으면 REPORT.md, ACTIONS.md, README_RUN.md 를 루트에 둔다.

## 2. 보고서
```
AGENTS.md 를 따른다. harness/templates/REPORT.md 형식으로 <지정 파일명> 초안을 써라.
숫자는 outputs/tables/ 에서 가져와 출처를 괄호로. 근거는 FINDINGS 의 강·중만. 한계 절에 REVIEW 의 수용-한계와 sensitivity 결과. 1장 이내.
```
결론 3줄과 메커니즘 문장은 사람이 직접 다시 쓴다.

## 3. 조치안
```
INTERVIEW 의 제약과 REVIEW 의 한계를 반영해 ACTIONS.md 를 써라. 즉시 조치 선택지 비교표(영향·리스크)와 추천안·이유, 확인 실험(설계·판정 기준), 하지 말 것. 최종 선택은 요청자에게 열어둬라.
```

## 4. 재현
```
src/run_all.py 를 harness/scaffold/run_all_template.py 기반으로 만들고, data/clean·outputs 를 비운 깨끗한 상태에서 실행해 모든 표·그림이 다시 생성되는지 확인하라.
README_RUN.md 를 템플릿대로 작성하라 (서버 실행 명령과 포트 포함).
```
```
rm -rf data/clean/* outputs/tables/* outputs/figures/*
python -m src.run_all && python -m pytest -q
git add -A && git commit -m "[S5] 산출물, clean run 통과"
```
서버가 있으면 재시작한다.

## 5. 요청자 최종 회신
요약 2줄 + 권고 조치 + 확인 요청. 답변을 INTERVIEW 에 기록.

## 6. 마무리 점검 (08 마감 뒤)
1. 에디터 저장 상태, 지정 파일 경로 확인
2. `git status` 깨끗한지, 최종 커밋 `[FINAL]`
3. 필요하면 태그: `git tag final`
