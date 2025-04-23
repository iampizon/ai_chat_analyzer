#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import os
import json
from analyze_chat_logs import split_csv_file, analyze_with_bedrock, combine_results

# 페이지 설정
st.set_page_config(
    page_title="Discord 채팅 로그 분석기",
    page_icon="📊",
    layout="wide"
)

# 제목
st.title("Discord 채팅 로그 분석기")

# 파일 업로드 섹션
st.header("1. CSV 파일 업로드")
uploaded_file = st.file_uploader("Discord 채팅 로그 CSV 파일을 업로드하세요", type=['csv'])

if uploaded_file is not None:
    # 업로드된 파일을 임시로 저장
    with open('./uploaded_log.csv', 'wb') as f:
        f.write(uploaded_file.getvalue())
    
    st.success("파일이 성공적으로 업로드되었습니다!")
    
    # 분석 시작 버튼
    if st.button("분석 시작"):
        # 진행 상황을 표시할 프로그레스 바
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 1. 파일 분할
            status_text.text("파일을 분할하는 중...")
            chunk_files = split_csv_file()
            total_chunks = len(chunk_files)
            progress_bar.progress(0.2)
            
            # 2. 각 청크 분석
            result_files = []
            for idx, chunk_file in enumerate(chunk_files, 1):
                status_text.text(f"청크 {idx}/{total_chunks} 분석 중...")
                result_file = analyze_with_bedrock(chunk_file, idx, total_chunks)
                result_files.append(result_file)
                progress_bar.progress(0.2 + (0.6 * (idx/total_chunks)))
            
            # 3. 결과 종합
            status_text.text("최종 분석 결과 생성 중...")
            final_result = combine_results(result_files)
            progress_bar.progress(1.0)
            status_text.text("분석이 완료되었습니다!")
            
            # 결과 표시 섹션
            st.header("2. 분석 결과")
            
            # 탭 생성
            tab1, tab2, tab3 = st.tabs(["청크 파일", "분석 결과", "최종 결과"])
            
            # 청크 파일 목록
            with tab1:
                st.subheader("생성된 청크 파일")
                for chunk_file in chunk_files:
                    if os.path.exists(chunk_file):
                        with open(chunk_file, 'r', encoding='utf-8') as f:

                            # 파일 내용 미리보기
                            with st.expander(f"미리보기: {os.path.basename(chunk_file)}"):
                                df = pd.read_csv(chunk_file)
                                st.dataframe(df.head())
            
            # 분석 결과 파일 목록
            with tab2:
                st.subheader("청크별 분석 결과")
                for result_file in result_files:
                    if result_file and os.path.exists(result_file):
                        with open(result_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            with st.expander(f"분석 결과: {os.path.basename(result_file)}"):
                                try:
                                    # JSON 형식으로 표시
                                    st.json(json.loads(content))
                                except json.JSONDecodeError:
                                    # 일반 텍스트로 표시
                                    st.text(content)
                                
            
            # 최종 분석 결과
            with tab3:
                st.subheader("최종 분석 결과")
                if final_result and os.path.exists(final_result):
                    with open(final_result, 'r', encoding='utf-8') as f:
                        content = f.read()
                        try:
                            # JSON 형식으로 표시
                            st.json(json.loads(content))
                        except json.JSONDecodeError:
                            # 일반 텍스트로 표시
                            st.text(content)
                        
        
        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
            
else:
    st.info("분석을 시작하려면 CSV 파일을 업로드해주세요.")

# 사이드바에 도움말 추가
with st.sidebar:
    st.header("사용 방법")
    st.markdown("""
    1. CSV 파일 업로드
        - Discord 채팅 로그 CSV 파일을 선택하여 업로드합니다.
    
    2. 분석 시작
        - 파일 업로드 후 '분석 시작' 버튼을 클릭합니다.
        - 분석은 다음 단계로 진행됩니다:
            * 파일 분할
            * 청크별 분석
            * 최종 결과 생성
    
    3. 결과 확인
        - 청크 파일: 분할된 CSV 파일들을 확인하고 다운로드
        - 분석 결과: 각 청크별 상세 분석 결과
        - 최종 결과: 전체 데이터에 대한 종합 분석
    """)