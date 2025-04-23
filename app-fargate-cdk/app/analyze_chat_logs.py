#!/usr/bin/env python3
import os
import csv
import math
import boto3
import json
import time
import random
from datetime import datetime
from botocore.exceptions import ClientError

# 파일 경로 설정
INPUT_FILE = './uploaded_log.csv'
OUTPUT_DIR = './chat_chunks'
RESULTS_DIR = './analysis_results'

# 청크 크기 설정 (대략 토큰 수로 환산했을 때 모델 입력 제한에 맞게 조정)
# Anthropic Claude 모델의 경우 약 100,000 토큰 제한이 있으나, 
# 안전하게 사용하기 위해 더 작은 크기로 분할
MAX_ROWS_PER_CHUNK = 1000

# 재시도 설정
MAX_RETRIES = 5
RETRY_DELAY = 30  # 초 단위

# 디렉토리 생성
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

def split_csv_file():
    """CSV 파일을 여러 청크로 분할하여 저장"""
    print(f"파일 분할 시작: {INPUT_FILE}")
    
    # 전체 행 수 계산
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # 헤더 저장
        total_rows = sum(1 for _ in reader)
    
    # 청크 수 계산
    num_chunks = math.ceil(total_rows / MAX_ROWS_PER_CHUNK)
    print(f"총 {total_rows}개의 메시지를 {num_chunks}개의 청크로 분할합니다.")
    
    # 파일 분할
    chunk_files = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        for chunk_idx in range(num_chunks):
            chunk_rows = []
            chunk_rows.append(header)  # 각 청크에 헤더 추가
            
            # 청크에 행 추가
            for _ in range(MAX_ROWS_PER_CHUNK):
                try:
                    row = next(reader)
                    chunk_rows.append(row)
                except StopIteration:
                    break
            
            # 청크 파일 저장
            chunk_filename = f"{OUTPUT_DIR}/chunk_{chunk_idx+1}_of_{num_chunks}.csv"
            with open(chunk_filename, 'w', encoding='utf-8', newline='') as chunk_file:
                writer = csv.writer(chunk_file)
                writer.writerows(chunk_rows)
            
            chunk_files.append(chunk_filename)
            print(f"청크 {chunk_idx+1}/{num_chunks} 저장 완료: {chunk_filename}")
    
    return chunk_files

def invoke_model_with_retry(bedrock_runtime, model_id, prompt, chunk_idx, total_chunks):
    """재시도 로직이 포함된 모델 호출 함수"""
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "temperature": 0.2,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
            
            # 응답 처리
            response_body = json.loads(response.get('body').read())
            analysis_result = response_body.get('content')[0].get('text')
            return analysis_result
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                retries += 1
                wait_time = RETRY_DELAY + random.uniform(0, 5)  # 약간의 무작위성 추가
                print(f"ThrottlingException 발생. 청크 {chunk_idx}/{total_chunks} 처리 중 {retries}/{MAX_RETRIES} 재시도. {wait_time:.1f}초 대기 중...")
                time.sleep(wait_time)
            else:
                print(f"오류 발생: {e}")
                raise
        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}")
            raise
    
    raise Exception(f"최대 재시도 횟수({MAX_RETRIES})를 초과했습니다.")

def analyze_with_bedrock(chunk_file, chunk_idx, total_chunks):
    """AWS Bedrock을 사용하여 채팅 로그 청크 분석"""
    print(f"청크 {chunk_idx}/{total_chunks} 분석 시작: {chunk_file}")
    
    # 여러 리전에서 사용 가능한 Bedrock 클라이언트 초기화
    # us-west-2는 Claude 모델이 사용 가능한 리전 중 하나입니다
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-west-2'  # 크로스 리전 인퍼런싱이 가능한 리전으로 변경
    )
    
    # 청크 파일 읽기
    with open(chunk_file, 'r', encoding='utf-8') as f:
        chunk_content = f.read()
    
    # 프롬프트 구성
    prompt = f"""
    다음은 플레이투게더라는 소셜 온라인 게임의 Discord 채팅 로그입니다. 
    이 데이터를 분석하여 다음 정보를 제공해주세요:
    
    1. 가장 활발한 사용자 5명과 그들의 메시지 빈도
    2. 주요 대화 주제와 키워드
    3. 사용자들이 자주 언급하는 게임 기능이나 문제점
    4. 사용자 감정 분석 (긍정적/부정적/중립적 의견의 비율)
    5. 게임 개선을 위한 제안사항
    
    이 데이터는 전체 로그의 일부분(청크 {chunk_idx}/{total_chunks})입니다.
    
    CSV 데이터:
    {chunk_content}
    
    JSON 형식으로 분석 결과를 제공해주세요.
    """
    
    # 크로스 리전 인퍼런싱이 가능한 모델 선택
    # Claude 3 Sonnet은 여러 리전에서 사용 가능합니다
    # model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

    try:
        # 재시도 로직이 포함된 모델 호출
        analysis_result = invoke_model_with_retry(bedrock_runtime, model_id, prompt, chunk_idx, total_chunks)
        
        # 결과 저장
        result_filename = f"{RESULTS_DIR}/analysis_chunk_{chunk_idx}_of_{total_chunks}.json"
        with open(result_filename, 'w', encoding='utf-8') as f:
            f.write(analysis_result)
        
        print(f"청크 {chunk_idx}/{total_chunks} 분석 완료: {result_filename}")
        return result_filename
    
    except Exception as e:
        print(f"청크 {chunk_idx}/{total_chunks} 분석 중 오류 발생: {str(e)}")
        return None

def combine_results(result_files):
    """모든 청크의 분석 결과를 종합"""
    print("분석 결과 종합 시작")
    
    all_results = []
    for result_file in result_files:
        if result_file and os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                try:
                    result = json.loads(f.read())
                    all_results.append(result)
                except json.JSONDecodeError:
                    # JSON이 아닌 경우 텍스트 그대로 저장
                    with open(result_file, 'r', encoding='utf-8') as f:
                        all_results.append(f.read())
    
    # 종합 분석을 위해 Bedrock 호출
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-west-2'  # 크로스 리전 인퍼런싱이 가능한 리전으로 변경
    )
    
    # 프롬프트 구성
    prompt = f"""
    다음은 플레이투게더라는 소셜 온라인 게임의 Discord 채팅 로그를 여러 부분으로 나누어 분석한 결과입니다.
    이 분석 결과들을 종합하여 전체적인 인사이트를 제공해주세요:
    
    {json.dumps(all_results, indent=2, ensure_ascii=False)}
    
    다음 정보를 포함한 종합 보고서를 작성해주세요:
    
    1. 가장 활발한 사용자와 그들의 영향력
    2. 주요 대화 주제와 트렌드
    3. 게임에 대한 사용자 만족도와 불만 사항
    4. 시간에 따른 사용자 활동 패턴
    5. 게임 개발자에게 제안할 개선 사항
    
    JSON 형식으로 종합 분석 결과를 제공해주세요.
    """
    
    # 크로스 리전 인퍼런싱이 가능한 모델 선택
    model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    try:
        # 재시도 로직이 포함된 모델 호출
        final_analysis = invoke_model_with_retry(bedrock_runtime, model_id, prompt, "종합", "종합")
        
        # 최종 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_result_filename = f"{RESULTS_DIR}/final_analysis_{timestamp}.json"
        with open(final_result_filename, 'w', encoding='utf-8') as f:
            f.write(final_analysis)
        
        print(f"종합 분석 완료: {final_result_filename}")
        return final_result_filename
    
    except Exception as e:
        print(f"종합 분석 중 오류 발생: {str(e)}")
        return None

def main():
    """메인 실행 함수"""
    print("플레이투게더 Discord 채팅 로그 분석 시작")
    
    # 1. 파일 분할
    chunk_files = split_csv_file()
    total_chunks = len(chunk_files)
    
    # 2. 각 청크 분석
    result_files = []
    for idx, chunk_file in enumerate(chunk_files, 1):
        result_file = analyze_with_bedrock(chunk_file, idx, total_chunks)
        result_files.append(result_file)
    
    # 3. 결과 종합
    final_result = combine_results(result_files)
    
    if final_result:
        print(f"분석이 완료되었습니다. 최종 결과: {final_result}")
    else:
        print("분석 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main()