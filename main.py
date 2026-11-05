import re
from itertools import permutations
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="송탄고 급식 연관 규칙 분석", layout="wide")


# 데이터 로드 및 전처리 함수
@st.cache_data
def load_and_process_data(url):
    df = pd.read_csv(url, encoding="utf-8")

    total_days = len(df)
    baskets = []
    all_items = set()

    for raw_menu in df["메뉴"].dropna():
        # 괄호 및 괄호 안 내용 제거
        cleaned_menu = re.sub(r"\(.*?\)", "", str(raw_menu))
        # 세로줄(|) 기준으로 분리 및 공백 제거
        items = list(
            set(
                [
                    item.strip()
                    for item in cleaned_menu.split("|")
                    if item.strip()
                ]
            )
        )

        if items:
            baskets.append(items)
            all_items.update(items)

    return df, baskets, total_days, len(all_items)


# 연관 규칙 생성 함수
@st.cache_data
def generate_association_rules(baskets, total_days):
    item_counts = {}
    pair_counts = {}

    for basket in baskets:
        # 단일 품목 빈도수
        for item in basket:
            item_counts[item] = item_counts.get(item, 0) + 1

        # 함께 나온 품목 쌍 빈도수 (순서 고려)
        for cond, res in permutations(basket, 2):
            pair_counts[(cond, res)] = pair_counts.get((cond, res), 0) + 1

    rules = []
    for (cond, res), count in pair_counts.items():
        support = count / total_days
        confidence = count / item_counts[cond]
        lift = confidence / (item_counts[res] / total_days)

        rules.append(
            {
                "조건": cond,
                "결과": res,
                "동시": count,
                "지지도": round(support, 4),
                "신뢰도": round(confidence, 4),
                "향상도": round(lift, 4),
            }
        )

    rules_df = pd.DataFrame(rules)
    return rules_df, item_counts, pair_counts


# 데이터 불러오기
DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"
_, baskets, total_days, total_items = load_and_process_data(DATA_URL)
rules_df, item_counts, pair_counts = generate_association_rules(baskets, total_days)

st.title("🍱 송탄고 급식 메뉴 연관 규칙 분석")

# 사이드바 설정
st.sidebar.header("필터 및 정렬 설정")

# 메뉴 선택 필터 (규칙 필터링용)
all_menu_list = sorted(
    list(set(rules_df["조건"].tolist() + rules_df["결과"].tolist()))
)
selected_menu = st.sidebar.
