import re
from itertools import permutations
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="급식 규칙 찾기", layout="wide")


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

    # 비순서 쌍 개수 계산 (메뉴 쌍 수)
    unique_pairs = set()
    for basket in baskets:
        sorted_b = sorted(list(basket))
        for i in range(len(sorted_b)):
            for j in range(i + 1, len(sorted_b)):
                unique_pairs.add((sorted_b[i], sorted_b[j]))

    return rules_df, item_counts, pair_counts, len(unique_pairs)


# 데이터 불러오기
DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"
_, baskets, total_days, total_items = load_and_process_data(DATA_URL)
rules_df, item_counts, pair_counts, total_pair_count = generate_association_rules(
    baskets, total_days
)

# --- 상단 타이틀 및 설명 ---
st.title("🍱 급식 규칙 찾기")
st.caption("송탄고 중식 · 하루 식단을 장바구니 1건으로 계산합니다.")

# --- 메트릭 3개 배치 ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="급식 일수", value=f"{total_days}일")
with col2:
    st.metric(label="메뉴 종류 수", value=f"{total_items}종")
with col3:
    st.metric(label="함께 나온 메뉴 쌍", value=f"{total_pair_count:,}쌍")

st.caption(
    "메뉴 쌍은 순서를 구분하지 않은 개수이며, 아래 규칙 표에는 조건과 결과를 바꾼 두 방향이 모두 포함됩니다."
)
st.write("")

# --- 필터 및 컨트롤 영역 ---
all_menu_list = sorted(
    list(set(rules_df["조건"].tolist() + rules_df["결과"].tolist()))
)

f_col1, f_col2 = st.columns(2)
with f_col1:
    selected_menu = st.selectbox(
        "규칙 좁혀 보기: 메뉴 선택",
        ["전체 메뉴"] + all_menu_list,
        key="rule_filter_menu"
    )

with f_col2:
    sort_option = st.selectbox(
        "정렬 기준",
        ["향상도 순", "신뢰도 순", "동시 순"],
        key="rule_sort_option"
    )

min_co_occur = st.slider(
    "최소 동시 등장 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    key="min_co_occur_slider"
)

# 데이터 필터링 (최소 동시 일수 및 선택 메뉴)
filtered_df = rules_df[rules_df["동시"] >= min_co_occur].copy()

if selected_menu != "전체 메뉴":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]

# 정렬 적용
sort_column_map = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시",
}
sort_col = sort_column_map[sort_option]

filtered_df = filtered_df.sort_values(
    by=[sort_col, "동시"], ascending=False
).reset_index(drop=True)

st.divider()

# --- 연관 규칙 표 및 막대 그래프 ---
st.subheader("연관규칙 표")
st.write(
    f"최소 {min_co_occur}일 이상 함께 등장한 규칙은 **{len(filtered_df)}개**입니다. (양방향 규칙 포함)"
)

# Plotly 가로 막대그래프 (향상도 상위 10개)
top_10_lift = filtered_df.sort_values(by="향상도", ascending=False).head(10)

if not top_10_lift.empty:
    top_10_lift["규칙"] = top_10_lift["조건"] + " ➔ " + top_10_lift["결과"]

    fig = px.bar(
        top_10_lift.sort_values(by="향상도", ascending=True),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        title=f"향상도 상위 10개 규칙 ({'전체' if selected_menu == '전체 메뉴' else selected_menu})",
        labels={"향상도": "향상도", "규칙": "연관 규칙"},
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        height=400,
        xaxis=dict(range=[0, max(top_10_lift["향상도"]) * 1.15])
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("조건에 해당하는 규칙이 없습니다.")

# 연관 규칙 데이터프레임 표 출력
st.dataframe(filtered_df, use_container_width=True)

st.divider()

# --- 함께 나온 적 없는 짝 탐색 섹션 ---
st.subheader("🔍 함께 나온 적 없는 짝 탐색")
st.caption(
    "선택한 메뉴와 단 한 번도 함께 나온 적이 없으면서, 전체 기간 중 10일 이상 제공된 메뉴 목록입니다."
)

unpaired_selected_menu = st.selectbox(
    "기준 메뉴 선택 (함께 나온 적 없는 메뉴 탐색용)",
    all_menu_list,
    key="unpaired_menu_select",
)

if unpaired_selected_menu:
    selected_menu_days = item_counts.get(unpaired_selected_menu, 0)

    # 기준 메뉴와 같은 날 한 번이라도 같이 등장한 메뉴들 추출
    together_menus = set()
    for (cond, res), count in pair_counts.items():
        if cond == unpaired_selected_menu and count > 0:
            together_menus.add(res)

    # 조건 판단:
    # 1. 자기 자신이 아닐 것
    # 2. 같이 나온 적이 없을 것
    # 3. 단독 출현 일수가 10일 이상일 것
    never_together = []
    for menu, count in item_counts.items():
        if (
            menu != unpaired_selected_menu
            and menu not in together_menus
            and count >= 10
        ):
            never_together.append({"메뉴": menu, "제공 일수": count})

    never_together_df = pd.DataFrame(never_together)

    st.markdown(
        f"**'{unpaired_selected_menu}'** 메뉴가 나온 날 수: **{selected_menu_days}일**"
    )

    if not never_together_df.empty:
        never_together_df = never_together_df.sort_values(
            by="제공 일수", ascending=False
        ).reset_index(drop=True)
        st.dataframe(never_together_df, use_container_width=True)
    else:
        st.info(
            "해당 조건(함께 나온 적 없고 단독 10일 이상 출현)을 만족하는 메뉴가 없습니다."
        )
