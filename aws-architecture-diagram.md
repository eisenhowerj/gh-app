# GitHub App AWS Architecture Diagram

```mermaid
graph TB
    %% External components
    GitHub[GitHub Webhooks<br/>🐙] 
    User[User/Developer<br/>👤]
    Internet[Internet<br/>🌐]
    
    %% DNS and Domain
    subgraph "DNS & SSL"
        HostedZone[Route53 Hosted Zone<br/>synthesis.run]
        Certificate[ACM Certificate<br/>scmaestro.synthesis.run]
        ARecord[Route53 A Record<br/>scmaestro.synthesis.run]
    end
    
    %% Security Layer
    subgraph "Security"
        WAF[AWS WAF<br/>Web ACL]
        IPv4Set[IPv4 IP Set<br/>GitHub IPs]
        IPv6Set[IPv6 IP Set<br/>GitHub IPs]
    end
    
    %% API Layer
    subgraph "API Gateway"
        CustomDomain[Custom Domain<br/>scmaestro.synthesis.run]
        API[API Gateway<br/>REST API]
        Stage[API Stage<br/>prod]
    end
    
    %% Compute Layer
    subgraph "Compute"
        Lambda[Lambda Function<br/>Python 3.13<br/>GitHub Webhook Handler]
        LogGroup[CloudWatch Log Group]
    end
    
    %% Storage & Secrets
    subgraph "Storage & Configuration"
        Secrets[Secrets Manager<br/>GitHub App Credentials]
    end
    
    %% Monitoring
    subgraph "Monitoring"
        Dashboard[CloudWatch Dashboard<br/>GhecWebhookProcessor]
        Metrics[CloudWatch Metrics<br/>Invocations, Errors, Duration, Throttles]
        LogWidget[Log Query Widget<br/>Recent 20 entries]
    end
    
    %% Output
    Output[CloudFormation Output<br/>Update Secrets Command]
    
    %% External connections
    GitHub -->|Webhook POST| Internet
    User -->|HTTPS Requests| Internet
    Internet -->|DNS Resolution| HostedZone
    
    %% DNS Flow
    HostedZone -->|Domain Validation| Certificate
    ARecord -->|Alias Target| CustomDomain
    Certificate -->|SSL/TLS| CustomDomain
    
    %% Security Flow
    Internet -->|Filter by IP| WAF
    IPv4Set -->|Referenced by| WAF
    IPv6Set -->|Referenced by| WAF
    WAF -->|Allow GitHub IPs| CustomDomain
    
    %% API Flow
    CustomDomain -->|Base Path Mapping| API
    API -->|Proxy Integration| Lambda
    Stage -->|Association| WAF
    
    %% Compute Flow
    Lambda -->|Read Secrets| Secrets
    Lambda -->|Write Logs| LogGroup
    Lambda -->|Generate Metrics| Metrics
    
    %% Monitoring Flow
    Metrics -->|Display| Dashboard
    LogGroup -->|Query| LogWidget
    LogWidget -->|Add to| Dashboard
    
    %% Output Flow
    Secrets -->|Reference| Output
    
    %% Styling
    classDef external fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef aws fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef security fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef compute fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef monitoring fill:#fff8e1,stroke:#f9a825,stroke-width:2px
    
    class GitHub,User,Internet external
    class HostedZone,Certificate,ARecord,CustomDomain,API,Stage,Lambda,LogGroup,Secrets,Output aws
    class WAF,IPv4Set,IPv6Set security
    class Lambda,LogGroup compute
    class Dashboard,Metrics,LogWidget monitoring
```

## Resource Relationships Summary

### Security Flow
1. **WAF Protection**: GitHub webhooks must come from approved IP ranges (IPv4/IPv6 sets)
2. **SSL Termination**: ACM certificate provides HTTPS encryption
3. **Domain Validation**: Route53 validates certificate ownership

### Request Flow
1. **GitHub** sends webhook → **Internet**
2. **DNS Resolution** via **Route53 Hosted Zone**
3. **WAF Filtering** checks source IP against GitHub IP sets
4. **Custom Domain** routes to **API Gateway**
5. **API Gateway** proxies request to **Lambda Function**
6. **Lambda** processes webhook and reads **Secrets Manager**

### Monitoring Flow
1. **Lambda** generates metrics and logs
2. **CloudWatch Dashboard** displays:
   - Function invocations, errors, duration, throttles
   - Recent log entries (last 20)
3. **Operational Output** provides command to update secrets

### Key Security Features
- **IP Whitelisting**: Only GitHub webhook IPs allowed
- **HTTPS Only**: Custom domain with ACM certificate
- **Secrets Management**: GitHub credentials stored securely
- **Monitoring**: Comprehensive dashboard for operational visibility
