# 시스템 아키텍처

> 문서 상태: [진행 중]

```mermaid
flowchart TB
    DM[DohaMusic Product Service / Job Orchestrator]
    API[DohaVocal Provider HTTP API Foundation - 구현]
    APP[Job Service]
    CAP[Capability Interface]
    ADP[Fake Provider - metadata only]
    ART[(In-memory Artifact metadata)]

    DM --> API --> APP --> CAP --> ADP --> ART
    ART -->|Artifact ID와 Metadata| DM
```

DohaMusic이 사용 권한, 입력 선택, GPU admission, Provider 순서와 Workspace 상태를 관리합니다. DohaVocal은 할당된 기술 처리와 Provider 내부 자원을 관리합니다.

현재 구현은 `API → Application Service → Provider interface → Fake Provider` 경계를 검증합니다. 실제 Model Adapter, Artifact payload 저장소, queue/worker와 Production persistence는 [미구현]입니다.
