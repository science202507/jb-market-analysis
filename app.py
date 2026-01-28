import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib  # ✅ 이 한 줄이 서버에 한글 폰트를 심어줍니다.
import re

# [주의] plt.rcParams['font.family'] = 'Malgun Gothic' 같은 코드는 절대 넣지 마세요!

st.set_page_config(page_title="전북 상권 분석기", layout="wide")

@st.cache_data
def load_data():
    def smart_read(file_name):
        for enc in ['utf-8-sig', 'cp949', 'utf-8', 'euc-kr']:
            try:
                df = pd.read_csv(file_name, encoding=enc)
                if not df.empty: return df
            except: continue
        return None
    store = smart_read('store_data.csv')
    pop = smart_read('age.csv')
    if store is None or pop is None: return None, None, None, None
    pop_col = [col for col in pop.columns if '총인구수' in col][0]
    pop[pop_col] = pop[pop_col].astype(str).str.replace(',', '').astype(int)
    pop['지역명_정제'] = pop['행정구역'].apply(lambda x: x.split('(')[0].strip())
    age_cols = [col for col in pop.columns if '세' in col]
    return store, pop, pop_col, age_cols

store_df, pop_df, total_pop_col, age_cols = load_data()

if store_df is None:
    st.error("데이터 파일을 찾을 수 없습니다.")
    st.stop()

st.title("🎯 전라북도 타겟 상권 밀도 분석기")
st.sidebar.header("🔍 설정")

region_list = sorted(store_df['시군구명'].unique().tolist())
industry_list = sorted(store_df['상권업종중분류명'].unique().tolist())

selected_regions = st.sidebar.multiselect("비교 지역", region_list, default=[region_list[0]])
selected_industry = st.sidebar.selectbox("업종", industry_list)
age_range = st.sidebar.slider("타겟 연령", 0, 100, (20, 39))

if st.sidebar.button("분석 시작!"):
    results = []
    sel_age_cols = []
    for col in age_cols:
        match = re.search(r'(\d+)세', col)
        if match:
            age = int(match.group(1))
            if age_range[0] <= age <= age_range[1]: sel_age_cols.append(col)
        elif '100세 이상' in col and age_range[1] == 100: sel_age_cols.append(col)

    for region in selected_regions:
        cnt = len(store_df[(store_df['시군구명'] == region) & (store_df['상권업종중분류명'] == selected_industry)])
        pop_match = pop_df[pop_df['지역명_정제'].str.contains(region, na=False)]
        if not pop_match.empty:
            row = pop_match.iloc[0]
            t_pop = sum([int(str(row[c]).replace(',', '')) for c in sel_age_cols if str(row[c]).replace(',', '').isdigit()])
            results.append({
                '지역': region, '점포수': cnt, '타겟인구': t_pop,
                '타겟밀도': round((cnt / t_pop * 1000), 2) if t_pop > 0 else 0
            })

    if results:
        res_df = pd.DataFrame(results)
        st.subheader(f"📊 {age_range[0]}세~{age_range[1]}세 분석 결과")
        st.dataframe(res_df, use_container_width=True)
        
        # 그래프 출력
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=res_df, x='지역', y='타겟밀도', hue='지역', palette='Oranges_d', ax=ax)
        st.pyplot(fig)
