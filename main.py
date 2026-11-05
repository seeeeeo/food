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
selected_menu = st.sidebar.selectbox(
    "메뉴 선택 (전체 보기 또는 특정 메뉴 선택)", ["전체"] + all_menu_list
)

# 최소 동시 일수 슬라이더
min_co_occur = st.sidebar.slider(
    "최소 동시 일수", min_value=1, max_value=10, value=1, step=1
)

# 정렬 기준 선택
sort_option = st.sidebar.radio(
    "정렬 기준 선택", ("향상도", "신뢰도", "동시"), index=0
)

# 데이터 필터링 (메뉴 선택 및 최소 동시 일수)
filtered_df = rules_df[rules_df["동시"] >= min_co_occur].copy()

if selected_menu != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]

filtered_df = filtered_df.sort_values(
    by=[sort_option, "동시"], ascending=False
).reset_index(drop=True)

# 상단 기본 요약 정보
unique_pairs_count = len(filtered_df)
st.markdown(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {total_items}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {unique_pairs_count}개"
)

# 슬라이더 설정 결과 표시
st.info(f"💡 최소 동시 일수 {min_co_occur}일 이상 조건을 만족하는 남은 규칙은 총 **{len(filtered_df)}개**입니다.")
st.divider()

# Plotly 가로 막대그래프 (향상도 상위 10개)
st.subheader("📊 향상도 상위 10개 규칙")
top_10_lift = filtered_df.sort_values(by="향상도", ascending=False).head(10)

if not top_10_lift.empty:
    top_10_lift["규칙"] = top_10_lift["조건"] + " ➔ " + top_10_lift["결과"]

    fig = px.bar(
        top_10_lift.sort_values(by="향상도", ascending=True),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        title=f"향상도 TOP 10 ({'전체' if selected_menu == '전체' else selected_menu + ' 관련'})",
        labels={"향상도": "향상도 (Lift)", "규칙": "연관 규칙 (조건 ➔ 결과)"},
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=400, xaxis=dict(range=[0, max(top_10_lift["향상도"]) * 1.15]))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("조건에 해당하는 규칙이 없습니다.")
