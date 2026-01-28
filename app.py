import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="전북 타겟 상권 분석기", layout="wide")

# [보완] 서버 환경에서 한글 깨짐 방지 설정
@st.cache_resource
def setup_font():
    plt.rcParams['axes.unicode_minus'] = False
    if os.name == 'nt': # 윈도우(내 컴퓨터)일 때만 맑은 고딕 적용
        plt.rcParams['font.family'] = 'Malgun Gothic'
    else: # 깃허브 서버(리눅스)일 때는 기본 폰트 사용 (한글 깨짐 최소화)
        plt.rcParams['font.family'] = 'sans-serif'

setup_font()

# 2. 데이터 로드 (에러 방지용 로직 강화)
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
    
    if store is None or pop is None:
        return None, None, None, None

    # 인구 데이터 전처리
    pop_col = [col for col in pop.columns if '총인구수' in col][0]
    pop[pop_col] = pop[pop_col].astype(str).str.replace(',', '').astype(int)
    pop['지역명_정제'] = pop['행정구역'].apply(lambda x: x.split('(')[0].strip())
    
    # 연령별 컬럼 추출
    age_cols = [col for col in pop.columns if '세' in col]
    
    return store, pop, pop_col, age_cols

store_df, pop_df, total_pop_col, age_cols = load_data()

# 3. 앱 화면 구성
if store_df is None:
    st.error("❌ 데이터 파일(store_data.csv 또는 age.csv)을 찾을 수 없거나 비어 있습니다.")
    st.info("💡 깃허브 저장소에 파일 이름이 정확히 소문자로 올라갔는지 확인해 주세요.")
    st.stop()

st.title("🎯 전라북도 타겟 상권 분석 대시보드")
st.sidebar.header("🔍 분석 조건 설정")

# 지역 및 업종 목록
region_list = sorted(store_df['시군구명'].unique().tolist())
industry_list = sorted(store_df['상권업종중분류명'].unique().tolist())

selected_regions = st.sidebar.multiselect("비교 지역 선택", region_list, default=[region_list[0]])
selected_industry = st.sidebar.selectbox("분석 업종 선택", industry_list)
age_range = st.sidebar.slider("타겟 연령대 설정", 0, 100, (20, 39))

if st.sidebar.button("💡 분석 시작"):
    results = []
    
    # 타겟 연령대 컬럼 필터링
    selected_age_cols = []
    for col in age_cols:
        match = re.search(r'(\d+)세', col)
        if match:
            age_val = int(match.group(1))
            if age_range[0] <= age_val <= age_range[1]:
                selected_age_cols.append(col)
        elif '100세 이상' in col and age_range[1] == 100:
            selected_age_cols.append(col)

    for region in selected_regions:
        # 점포 수 계산
        cnt = len(store_df[(store_df['시군구명'] == region) & (store_df['상권업종중분류명'] == selected_industry)])
        
        # 인구수 매칭
        pop_match = pop_df[pop_df['지역명_정제'].str.contains(region, na=False)]
        
        if not pop_match.empty:
            row = pop_match.iloc[0]
            total_p = row[total_pop_col]
            target_p = sum([int(str(row[c]).replace(',', '')) for c in selected_age_cols if str(row[c]).replace(',', '').isdigit()])
            
            results.append({
                '지역': region, 
                '점포수': cnt, 
                '타겟인구': target_p,
                '밀도(1천명당)': round((cnt / target_p * 1000), 2) if target_p > 0 else 0
            })

    if results:
        res_df = pd.DataFrame(results)
        st.subheader(f"📊 {age_range[0]}세~{age_range[1]}세 타겟 분석 결과")
        
        # 메트릭 표시
        m1, m2 = st.columns(2)
        m1.metric("선택 업종", selected_industry)
        m2.metric("최고 밀도 지역", res_df.loc[res_df['밀도(1천명당)'].idxmax(), '지역'])

        st.dataframe(res_df, use_container_width=True)

        # 그래프 시각화
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=res_df, x='지역', y='밀도(1천명당)', hue='지역', palette='viridis', ax=ax)
        st.pyplot(fig)
        
        # 지도 시각화 추가 (보너스 기능)
        st.subheader(f"📍 {selected_industry} 점포 분포 지도")
        map_data = store_df[(store_df['시군구명'].isin(selected_regions)) & 
                            (store_df['상권업종중분류명'] == selected_industry)][['위도', '경도']].dropna()
        map_data.columns = ['lat', 'lon']
        st.map(map_data)
        
    else:
        st.warning("분석 결과가 없습니다. 조건을 다시 확인하세요.")
