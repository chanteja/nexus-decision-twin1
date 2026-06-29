# NEXUS — Diagrams

Professional diagrams for the Decision Twin. They render natively on GitHub (Mermaid).

---

## 1 · The customer journey

```mermaid
flowchart LR
    A[Decision Twin<br/>capture how the org decides] --> B[Decision Graph<br/>connect every decision<br/>to its assumptions]
    B --> C[Future Explorer<br/>reason about a decision<br/>before committing]
    C --> D[Reality Verification<br/>seal it & check it<br/>against reality]
    D --> E[Decision Timeline<br/>what's changed today?]
    E --> F[Organizational Learning<br/>the twin gets sharper]
    F -.compounds.-> A
```

---

## 2 · The aha — assumption propagation through the Decision Graph

```mermaid
flowchart TD
    EV[Reality: Brazil demand grew ~6%, not >18%]:::ember --> AS{{Assumption falsified:<br/>"demand grows >18% YoY"}}:::ember
    AS --> D1[Launch Brazil GTM<br/>FAILED]:::fail
    AS --> D2[Mexico expansion<br/>0.59 → 0.09 · impact 63]:::risk
    AS --> D3[São Paulo center<br/>0.68 → 0.39 · impact 38]:::risk
    AS --> D4[LATAM pricing<br/>0.66 → 0.38 · impact 33]:::risk
    AS --> D5[LATAM sales org<br/>0.63 → 0.36 · impact 26]:::risk
    D2 --> R[Ranked revisions +<br/>the twin learns:<br/>falsification rate ↑]:::learn
    D3 --> R
    D4 --> R
    D5 --> R
    AS -. does NOT touch .-> U1[EU data platform<br/>unaffected]:::ok
    AS -. does NOT touch .-> U2[90-day sales motion<br/>unaffected]:::ok
    classDef ember fill:#3a1c16,stroke:#ff7a4d,color:#ffd9c9;
    classDef fail fill:#2a1116,stroke:#ff4d5e,color:#ffd0d6;
    classDef risk fill:#241a12,stroke:#ff7a4d,color:#ffe6d9;
    classDef ok fill:#10261f,stroke:#3fd6c2,color:#cdeee7;
    classDef learn fill:#163b39,stroke:#3fd6c2,color:#bff7ee;
```

---

## 3 · The flywheel

```mermaid
flowchart LR
    A[Decision] --> B[Reality Verification]
    B --> C[Organizational Learning]
    C --> D[Sharper Decision Twin]
    D --> E[Better recommendations]
    E --> F[More usage]
    F --> G[More verified decisions]
    G --> H[Higher switching cost]
    H --> D
    G --> A
```

The moat is the compounding record of verified enterprise decisions — not the technology.

---

## 4 · The "what's changed today?" loop (daily habit)

```mermaid
sequenceDiagram
    participant E as Executive
    participant T as Decision Timeline
    participant V as Reality Verification
    participant G as Decision Graph
    E->>T: open NEXUS (morning)
    T-->>E: "3 settled, 1 against expectation, 5 due this week"
    E->>G: what did the surprise propagate to?
    G-->>E: 4 decisions re-scored + ranked revisions
    E->>V: prove the failed call predated its outcome
    V-->>E: sealed before outcome ✓ · intact ✓ · anchored ✓
```

---

## 5 · One-slide AWS architecture (every service earns its place)

```mermaid
flowchart TB
    subgraph Product[The five capabilities · /twin/*]
      P1[Decision Twin]:::p
      P2[Decision Graph + live propagation]:::p
      P3[Future Explorer]:::p
      P4[Reality Verification]:::p
      P5[Decision Timeline]:::p
    end
    Product --> BR[Bedrock<br/>enterprise reasoning]:::aws
    Product --> DDB[DynamoDB<br/>Decision Graph store]:::aws
    EB[EventBridge<br/>continuous verification]:::aws --> LM[Lambda<br/>autonomous execution]:::aws
    LM --> ORA[Oracle settles outcome<br/>not self-graded]
    LM --> S3[S3 Object Lock<br/>immutable evidence]:::aws
    LM --> OTS[OpenTimestamps<br/>external time anchor]
    LM --> DDB
    BR --> DDB
    CW[CloudWatch<br/>observability]:::aws -.audits.-> LM
    IAM[IAM · KMS · Secrets Manager<br/>governance]:::aws -.secures.-> Product
    classDef p fill:#10192a,stroke:#3fd6c2,color:#e7e3d8;
    classDef aws fill:#161d2e,stroke:#e9c46a,color:#f3e6c4;
```

> Remove EventBridge + Lambda + S3 Object Lock and the autonomous verify-and-learn loop
> stops. That is why AWS is essential here, not incidental.

---

## 6 · Why not ChatGPT

```mermaid
flowchart LR
    Q[Same question] --> GPT[ChatGPT]:::gpt
    Q --> TW[Decision Twin]:::tw
    GPT --> GA[answers · forgets · cannot verify]:::gpt
    TW --> TA[remembers the org's decisions]:::tw
    TW --> TB[verifies them against reality]:::tw
    TW --> TC[learns from outcomes]:::tw
    TW --> TD[compounds decision intelligence]:::tw
    classDef gpt fill:#241a12,stroke:#9aa3b2,color:#cbd0d8;
    classDef tw fill:#10261f,stroke:#3fd6c2,color:#cdeee7;
```
