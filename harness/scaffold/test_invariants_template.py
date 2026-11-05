"""불변식 테스트 템플릿.
사용: 실제 데이터 열 이름에 맞게 상수만 바꿔 tests/test_invariants.py 로 복사한다.
"""
import os

import pandas as pd
import pytest

CLEAN = "data/clean/main_clean.csv"          # 정제 결과 파일
KEY = ["lot_id", "wafer_id"]                  # 유일해야 하는 키
VALUE_COL = "yield"                           # 범위 검사 대상
VALUE_RANGE = (0.0, 1.0)
CATEGORY_COL = "chamber"                      # 범주 정규화 대상
VALID_CATEGORIES = {"A", "B", "C"}
LOST_FILE = "outputs/tables/join_lost_keys.csv"   # 조인 손실 격리 파일
LOST_KEY = "lot_id"

pytestmark = pytest.mark.skipif(not os.path.exists(CLEAN), reason="정제 결과가 아직 없음")


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CLEAN)


def test_value_range(df):
    assert df[VALUE_COL].between(*VALUE_RANGE).all()


def test_key_unique(df):
    assert not df.duplicated(KEY).any()


def test_category_values(df):
    assert set(df[CATEGORY_COL].dropna().unique()) <= VALID_CATEGORIES


def test_lost_keys_isolated(df):
    if not os.path.exists(LOST_FILE):
        pytest.skip("조인 손실 파일 없음")
    lost = pd.read_csv(LOST_FILE)
    assert set(lost[LOST_KEY]).isdisjoint(set(df[LOST_KEY]))
