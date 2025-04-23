#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AppFargateStack } from '../lib/app-fargate-stack';

const app = new cdk.App();
new AppFargateStack(app, 'AIChatAnalyzerFargateStack', {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2'
  },
});
