import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os
import requests
import re

# 1. [핵심] 한글 폰트 강제 설치 함수
@st.cache_resource
def load_korean_font():
    # 나눔고딕 폰트 파일 경로
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        # 폰트 파일이 없으면 깃허브에서 직접 다운로드
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        res = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(res.content)
    
    # 폰트 등록
    fm.fontManager.addfont(font_path)
    font_name = fm.FontProperties(fname=font_path).get_name()
    plt.rc('font', family=font_name)
    plt.rcParams['axes.unicode_minus'] = False
    return font_name

# 폰트 적용
try:
    font_name = load_korean_font()
except:
    st.error("폰트 설치에 실패했습니다. 하지만 분석은 계속 진행합니다.")

# 2. 페이지 설정
st.set_page_config(page_title="전북 상권 분석기", layout="wide")

# 3. 데이터 로드 (smart_read)
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

# 4. 화면 구성 (지도는 뺐습니다!)
if store_df is None:
    st.error("파일을 찾을 수 없습니다.")
    st.stop()

st.title("🎯 전라북도 타겟 상권 밀도 분석기")

region_list = sorted(store_df['시군구명'].unique().tolist())
industry_list = sorted(store_df['상권업종중분류명'].unique().tolist())

selected_regions = st.sidebar.multiselect("비교 지역 선택", region_list, default=[region_list[0]])
selected_industry = st.sidebar.selectbox("분석 업종 선택", industry_list)
age_range = st.sidebar.slider("타겟 연령대", 0, 100, (20, 39))

if st.sidebar.button("분석 시작!"):
    results = []
    selected_age_cols = []
    for col in age_cols:
        match = re.search(r'(\d+)세', col)
        if match:
            age = int(match.group(1))
            if age_range[0] <= age <= age_range[1]: selected_age_cols.append(col)
        elif '100세 이상' in col and age_range[1] == 100: selected_age_cols.append(col)

    for region in selected_regions:
        cnt = len(store_df[(store_df['시군구명'] == region) & (store_df['상권업종중분류명'] == selected_industry)])
        pop_match = pop_df[pop_df['지역명_정제'].str.contains(region, na=False)]
        if not pop_match.empty:
            row = pop_match.iloc[0]
            t_pop = sum([int(str(row[c]).replace(',', '')) for c in selected_age_cols if str(row[c]).replace(',', '').isdigit()])
            results.append({
                '지역': region, '점포수': cnt, '타겟인구': t_pop,
                '밀도': round((cnt / t_pop * 1000), 2) if t_pop > 0 else 0
            })

    if results:
        res_df = pd.DataFrame(results)
        st.subheader(f"📊 {age_range[0]}~{age_range[1]}세 타겟 분석 결과")
        st.dataframe(res_df, use_container_width=True)
        
        # 그래프 그리기
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=res_df, x='지역', y='밀도', hue='지역', palette='viridis', ax=ax)
        # 폰트 명시적 재설정
        ax.set_title(f"{selected_industry} 타겟 밀도 비교", fontsize=15)
        st.pyplot(fig)
