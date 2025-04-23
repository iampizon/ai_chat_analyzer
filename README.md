# 채팅 로그 분석기 - ECS Fargate 배포

이 프로젝트는 AWS CDK를 사용하여 Streamlit 기반의 채팅 로그 분석 애플리케이션을 ECS Fargate에 배포하는 인프라를 정의합니다.

## 애플리케이션 설명

### app.py
`app.py`는 Streamlit 기반의 웹 애플리케이션으로, 채팅 로그를 분석하는 인터페이스를 제공합니다. 주요 기능은 다음과 같습니다:

- CSV 형식의 Discord 채팅 로그 파일 업로드
- 대용량 로그 파일을 작은 청크로 분할
- AWS Bedrock을 활용한 채팅 로그 분석
- 분석 결과 시각화 및 다운로드
- 사용자 친화적인 웹 인터페이스

애플리케이션은 포트 8501(Streamlit 기본 포트)에서 실행되며, Docker 컨테이너 내에서 호스팅됩니다.

### analyze_chat_logs.py
`analyze_chat_logs.py`는 채팅 로그 데이터를 분석하는 핵심 스크립트입니다. 주요 기능은 다음과 같습니다:

- 대용량 CSV 파일을 관리 가능한 청크로 분할
- AWS Bedrock의 Claude 모델을 활용한 텍스트 분석
- 사용자 활동 패턴 분석
- 대화 주제 및 감정 분석
- 여러 청크의 분석 결과를 종합한 최종 보고서 생성

이 스크립트는 Streamlit 애플리케이션에서 호출되어 분석 작업을 수행합니다.

## 프로젝트 구조

```
app-fargate-cdk/
├── app/                  # 애플리케이션 코드
│   ├── app.py            # Streamlit 웹 애플리케이션
│   ├── analyze_chat_logs.py  # 채팅 로그 분석 스크립트
│   ├── Dockerfile        # Docker 이미지 정의
│   └── requirements.txt  # Python 의존성
├── bin/                  # CDK 앱 진입점
│   └── app-fargate-cdk.ts
├── lib/                  # CDK 스택 정의
│   └── app-fargate-stack.ts
├── cdk.json              # CDK 설정
├── package.json          # npm 패키지 정의
└── tsconfig.json         # TypeScript 설정
```

## 사전 요구사항

- Node.js (v14 이상)
- AWS CLI 설정 (액세스 키, 시크릿 키)
- AWS CDK 설치 (`npm install -g aws-cdk`)
- Docker
- AWS Bedrock 접근 권한 (Claude 모델 사용)

## CDK로 배포하는 방법

### 1. 프로젝트 설정

먼저 프로젝트 디렉토리로 이동합니다:
```bash
cd app-fargate-cdk
```

필요한 의존성을 설치합니다:
```bash
npm install
```

### 2. AWS 환경 설정

AWS CLI가 올바르게 구성되어 있는지 확인합니다:
```bash
aws configure
```

AWS 계정에 CDK 부트스트랩을 적용합니다(처음 사용하는 경우):
```bash
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

### 3. IAM 권한 설정

애플리케이션이 AWS Bedrock을 사용하기 위해서는 적절한 IAM 권한이 필요합니다. 다음 권한을 ECS 작업 실행 역할에 추가해야 합니다:

- `bedrock:InvokeModel`
- `bedrock:ListFoundationModels`

CDK 스택에서 이러한 권한이 자동으로 추가되도록 설정되어 있습니다.

### 4. CDK 스택 배포

배포할 내용을 미리 확인합니다:
```bash
cdk diff
```

스택을 배포합니다:
```bash
cdk deploy
```

배포 중에 IAM 권한 변경에 대한 확인 메시지가 표시되면 `y`를 입력하여 승인합니다.

### 5. 배포 확인

배포가 완료되면 다음 명령으로 스택의 출력값을 확인할 수 있습니다:
```bash
cdk deploy --outputs-file outputs.json
```

출력된 로드 밸런서 DNS 이름을 통해 Streamlit 애플리케이션에 접근할 수 있습니다.

### 6. 애플리케이션 사용 방법

1. 웹 브라우저에서 로드 밸런서 DNS 주소에 접속합니다.
2. CSV 형식의 Discord 채팅 로그 파일을 업로드합니다.
3. "분석 시작" 버튼을 클릭하여 분석 프로세스를 시작합니다.
4. 분석이 완료되면 결과를 확인하고 다운로드할 수 있습니다.

### 7. 리소스 정리

더 이상 필요하지 않은 경우 다음 명령으로 모든 리소스를 삭제할 수 있습니다:
```bash
cdk destroy
```

## 애플리케이션 커스터마이징

실제 애플리케이션 요구사항에 맞게 다음 파일들을 수정하세요:

- `app/app.py`: Streamlit 애플리케이션 코드
- `app/analyze_chat_logs.py`: 채팅 로그 분석 로직
- `app/requirements.txt`: 필요한 Python 패키지
- `lib/app-fargate-stack.ts`: 인프라 설정 (메모리, CPU, 환경 변수 등)

## 로깅 및 모니터링

애플리케이션 로그는 CloudWatch Logs에서 확인할 수 있습니다. 로그 그룹 이름은 `/ecs/app`으로 시작합니다.

성능 모니터링을 위해 CloudWatch 대시보드를 설정하는 것을 권장합니다.

## 보안 고려사항

- 이 애플리케이션은 AWS Bedrock API를 사용하므로 적절한 IAM 권한 설정이 중요합니다.
- 민감한 채팅 로그를 처리하는 경우, 데이터 암호화 및 접근 제어를 고려하세요.
- 프로덕션 환경에서는 HTTPS를 활성화하고 인증 메커니즘을 추가하는 것이 좋습니다.

## 비용 최적화

- Fargate 작업의 CPU 및 메모리 설정을 애플리케이션 요구사항에 맞게 조정하세요.
- 사용량이 적을 때는 서비스의 작업 수를 줄이는 Auto Scaling 정책을 고려하세요.
- AWS Bedrock API 호출 비용을 모니터링하고 필요에 따라 사용량을 제한하세요.
