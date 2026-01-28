import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib  # 👈 한글 깨짐을 방지하는 핵심 라이브러리
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="전북 타겟 상권 분석기", layout="wide")

# 2. 데이터 로드 및 전처리
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

    # 인구 데이터 총인구수 전처리
    pop_col = [col for col in pop.columns if '총인구수' in col][0]
    pop[pop_col] = pop[pop_col].astype(str).str.replace(',', '').astype(int)
    pop['지역명_정제'] = pop['행정구역'].apply(lambda x: x.split('(')[0].strip())
    
    # 연령별 컬럼(0세~100세 이상) 식별
    age_cols = [col for col in pop.columns if '세' in col]
    
    return store, pop, pop_col, age_cols

store_df, pop_df, total_pop_col, age_cols = load_data()

# 3. 데이터 로드 실패 시 예외 처리
if store_df is None:
    st.error("❌ 'store_data.csv' 또는 'age.csv' 파일을 불러올 수 없습니다. 파일명을 확인해 주세요.")
    st.stop()

# 4. 앱 메인 화면
st.title("🎯 전라북도 타겟 상권 밀도 분석기")
st.sidebar.header("🔍 분석 조건 설정")

# 목록 추출
region_list = sorted(store_df['시군구명'].unique().tolist())
industry_list = sorted(store_df['상권업종중분류명'].unique().tolist())

# 사이드바 입력
selected_regions = st.sidebar.multiselect("비교할 지역을 선택하세요", region_list, default=[region_list[0]])
selected_industry = st.sidebar.selectbox("분석할 업종을 선택하세요", industry_list)

st.sidebar.divider()
st.sidebar.subheader("👥 타겟 고객층 설정")
age_range = st.sidebar.slider("분석할 타겟 연령 범위를 고르세요", 0, 100, (20, 39))

# 5. 분석 버튼 클릭 시 실행
if st.sidebar.button("타겟 분석 시작!"):
    results = []
    
    # 선택된 연령 범위에 해당하는 컬럼 찾기
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
        # 점포 수
        cnt = len(store_df[(store_df['시군구명'] == region) & (store_df['상권업종중분류명'] == selected_industry)])
        
        # 인구 데이터 매칭
        pop_match = pop_df[pop_df['지역명_정제'].str.contains(region, na=False)]
        
        if not pop_match.empty:
            row = pop_match.iloc[0]
            total_pop = row[total_pop_col]
            
            # 타겟 인구 합계 계산
            target_pop = 0
            for c in selected_age_cols:
                val = str(row[c]).replace(',', '')
                target_pop += int(val) if val.isdigit() else 0
            
            # 밀도 계산 (타겟 인구 1,000명당 점포 수)
            target_density = (cnt / target_pop) * 1000 if target_pop > 0 else 0
            
            results.append({
                '지역': region,
                '점포수': cnt,
                '전체인구': total_pop,
                '타겟인구': target_pop,
                '타겟밀도': round(target_density, 2)
            })

    if results:
        res_df = pd.DataFrame(results)
        
        # 결과 대시보드
        st.subheader(f"📊 {age_range[0]}세~{age_range[1]}세 타겟 분석 결과")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("선택 업종", selected_industry)
        m2.metric("타겟 연령", f"{age_range[0]}~{age_range[1]}세")
        m3.metric("최고 밀도 지역", res_df.loc[res_df['타겟밀도'].idxmax(), '지역'])

        st.dataframe(res_df, use_container_width=True)

        # 비교 그래프 (koreanize_matplotlib 덕분에 한글이 잘 나옵니다)
        st.write(f"🔥 **타겟 인구({age_range[0]}~{age_range[1]}세) 대비 점포 밀도** (단위: 개/1천명)")
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=res_df, x='지역', y='타겟밀도', hue='지역', palette='Oranges_d', ax=ax, legend=False)
        plt.xticks(rotation=45)
        st.pyplot(fig)

        # 결과 다운로드
        csv = res_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📂 분석 결과 다운로드 (CSV)", data=csv, file_name='target_analysis.csv', mime='text/csv')
    else:
        st.warning("분석할 데이터를 찾을 수 없습니다.")
