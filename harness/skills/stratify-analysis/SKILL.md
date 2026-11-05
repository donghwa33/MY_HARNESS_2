---
name: stratify-analysis
description: 결과를 그룹·기간·조건별로 나눠 보고, 후보 설명이나 방법을 같은 표에서 비교한다. 결론이 일부 데이터에만 기대는지 확인할 때, 값이 변한 원인을 찾을 때 사용한다.
---
# 나눠 보기

함수: harness/scaffold/analysis_utils.py (stratify, crosstab_counts, naive_vs_stratified, period_compare, bootstrap_diff, waterfall, save_table, save_fig)

## 순서
1. 나눌 기준을 정한다: 그룹·기간·조건 중 결론에 영향이 클 것. 집계 단위를 명시한다.
2. 나눈 결과를 한 표에 둔다: 셀별 값, 단위 수, 전체 대비 차이. 단위 수가 작은 셀은 표시한다.
3. 전체로 본 결과와 나눠 본 결과가 다르면 셀 구성의 쏠림(교차 빈도)으로 이유를 설명한다.
4. 다른 종류의 근거(다른 그룹·기간·데이터)로도 같은 결론이 나오는지 본다.
5. 값이 변한 원인을 찾는 경우: 변화 시점과 측정·조건 변경을 먼저 확인하고, 전체 변화를 후보별 기여와 잔차로 나눈다.
6. 주요 차이에 구간을 붙인다.

결과는 outputs/ 에 저장하고 FINDINGS 에 F-번호로 쓴다. 후보 하나만 따로 보지 않고 대안과 같은 표에서 비교한다.
