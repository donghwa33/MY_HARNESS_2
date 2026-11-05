---
name: handoff
description: 세션을 교대하거나 마감할 때 인계 문서를 쓴다. 사람이 handoff 를 요청하거나, 단계가 끝났거나, 맥락이 흐려졌을 때 사용한다.
---
# Handoff

1. work/HANDOFF.md 를 30줄 이내로 새로 쓴다 (harness/templates/HANDOFF.md):
   - 지난 인계 이후 완료된 작업
   - 다음 행동 3개
   - 유효 결정 번호와 어기면 생기는 일
   - 열린 질문
   - 실행 중인 서버(포트·명령)
   - 피해야 할 함정
2. 다른 문서 내용은 복사하지 않고 번호와 파일명으로 가리킨다.
3. STATE 를 갱신하고 `[HANDOFF-N]` 으로 커밋한다.
4. 새 세션 부팅 프롬프트를 출력한다 (harness/playbook/07_handoff.md).
