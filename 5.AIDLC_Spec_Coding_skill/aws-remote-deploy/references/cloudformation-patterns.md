# CloudFormation Patterns

## Baseline Remote Service Template

For a typical HTTP service, prefer these resources:

- VPC/subnet inputs or a nested/network stack reference.
- ALB security group allowing inbound `80` or `443`.
- Service security group allowing traffic only from the ALB security group.
- Application Load Balancer.
- Target group with a health check path.
- Listener and listener rules.
- Runtime service, commonly ECS Fargate, Lambda, or EC2 Auto Scaling depending on the project.
- CloudWatch log group.
- IAM execution/task roles with least privilege.
- Secrets Manager or SSM Parameter Store reference for API token material.
- Stack outputs for ALB DNS, base URL, target group ARN, log group, and token check command.

## ALB Header Gate Example

Use this only when exact token matching in listener configuration is acceptable for the target environment:

```yaml
ApiTokenListenerRule:
  Type: AWS::ElasticLoadBalancingV2::ListenerRule
  Properties:
    ListenerArn: !Ref HttpListener
    Priority: 10
    Conditions:
      - Field: http-header
        HttpHeaderConfig:
          HttpHeaderName: X-API-Token
          Values:
            - !Ref ApiTokenValue
      - Field: path-pattern
        Values:
          - /api/*
    Actions:
      - Type: forward
        TargetGroupArn: !Ref AppTargetGroup
```

Add a lower-priority deny/default rule:

```yaml
DefaultDenyAction:
  Type: AWS::ElasticLoadBalancingV2::ListenerRule
  Properties:
    ListenerArn: !Ref HttpListener
    Priority: 100
    Conditions:
      - Field: path-pattern
        Values:
          - /api/*
    Actions:
      - Type: fixed-response
        FixedResponseConfig:
          StatusCode: "403"
          ContentType: text/plain
          MessageBody: Forbidden
```

## Secure Token Handling

If a listener rule exact match would expose token values in CloudFormation parameters, stack events, operational views, or change history, prefer:

- ALB routing that requires the token header to be present when feasible.
- Server-side validation against Secrets Manager or SSM.
- Clear documentation that ALB provides the supported ingress gate and the server performs authoritative secret validation.

## CloudFormation Deploy Command Shape

```bash
aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE_FILE" \
  --parameter-overrides \
    EnvironmentName="$ENV_NAME" \
    ApiTokenSecretArn="$API_TOKEN_SECRET_ARN" \
  --tags \
    Project="$PROJECT_NAME" \
    Environment="$ENV_NAME" \
    ManagedBy="codex-aws-remote-deploy"
```

## When AWS CLI Fallback Is Justified

Use CLI fallback for:

- One-time artifact upload or image push not modeled in the stack.
- Bootstrapping a parameter or secret that must not appear in a template.
- Projects where the user explicitly asks for a shell-only proof of concept.

Do not use CLI fallback merely because CloudFormation syntax is longer.
