import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as path from 'path';

export class AppFargateStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC 생성
    const vpc = new ec2.Vpc(this, 'AIChatAnalyzerVpc', {
      maxAzs: 2,
      natGateways: 1
    });

    // ECS 클러스터 생성
    const cluster = new ecs.Cluster(this, 'AIChatAnalyzerCluster', {
      vpc: vpc,
      containerInsights: true,
    });

    // Docker 이미지 생성 (로컬 Dockerfile 사용)
    const appImage = new ecr_assets.DockerImageAsset(this, 'AIChatAnalyzerImage', {
      directory: path.join(__dirname, '../app'),
      platform: ecr_assets.Platform.LINUX_AMD64,  // 명시적으로 플랫폼 지정
    });

    // Bedrock 접근을 위한 IAM 정책 생성
    const bedrockPolicy = new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:ListFoundationModels',
      ],
      resources: ['*'],
      effect: iam.Effect.ALLOW,
    });

    // Fargate 작업 정의
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'AIChatAnalyzerTaskDef', {
      memoryLimitMiB: 512,
      cpu: 256,
    });

    // AWS Bedrock 권한 추가 - 작업 역할에 직접 추가
    const taskRole = taskDefinition.taskRole as iam.Role;
    taskRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonBedrockFullAccess')
    );

    // 또는 더 세분화된 권한 정책 추가
    taskRole.addToPolicy(bedrockPolicy);

    // 컨테이너 정의
    const container = taskDefinition.addContainer('AIChatAnalyzerContainer', {
      image: ecs.ContainerImage.fromDockerImageAsset(appImage),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'app',
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: {
        // 필요한 환경 변수 설정
        'NODE_ENV': 'production',
        'AWS_REGION': 'us-west-2',  // Bedrock 서비스가 있는 리전 명시
      },
    });

    // 포트 매핑
    container.addPortMappings({
      containerPort: 8501,  // Streamlit 기본 포트
      hostPort: 8501,
      protocol: ecs.Protocol.TCP,
    });

    // 보안 그룹 생성
    const securityGroup = new ec2.SecurityGroup(this, 'AIChatAnalyzerSecurityGroup', {
      vpc,
      description: 'Allow HTTP access to the app',
      allowAllOutbound: true,
    });
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(8501), 'Allow Streamlit traffic');

    // ALB 생성
    const alb = new elbv2.ApplicationLoadBalancer(this, 'AIChatAnalyzerLoadBalancer', {
      vpc,
      internetFacing: true,
      idleTimeout: cdk.Duration.seconds(180)  // 3분으로 설정
    });

    // ALB 리스너 생성
    const listener = alb.addListener('AIChatAnalyzerListener', {
      port: 80,
      open: true,
    });

    // Fargate 서비스 생성
    const service = new ecs.FargateService(this, 'AIChatAnalyzerService', {
      cluster,
      taskDefinition,
      desiredCount: 2,
      securityGroups: [securityGroup],
      assignPublicIp: false,
    });

    // ALB 타겟 그룹에 서비스 추가
    const targetGroup = listener.addTargets('AIChatAnalyzerTargetGroup', {
      port: 8501,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [service],
      healthCheck: {
        path: '/',
        interval: cdk.Duration.seconds(60),
        timeout: cdk.Duration.seconds(30),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
        healthyHttpCodes: '200,302'  // Streamlit은 종종 302 리다이렉트를 반환

      },

    });

    targetGroup.setAttribute('stickiness.enabled', 'true');
    targetGroup.setAttribute('stickiness.type', 'lb_cookie');
    targetGroup.setAttribute('stickiness.lb_cookie.duration_seconds', '86400');
    targetGroup.setAttribute('deregistration_delay.timeout_seconds', '30');
    targetGroup.setAttribute('load_balancing.algorithm.type', 'least_outstanding_requests');

    // 출력값 정의
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: alb.loadBalancerDnsName,
      description: 'The DNS name of the load balancer',
    });
  }
}
