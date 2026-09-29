# 아키텍처 결정 기록

> 문서 상태: [계획]

| ADR | 결정 | 상태 |
|---|---|---|
| [ADR-001](ADR-001-repository-boundary.md) | 저장소 책임 경계 | [제안] |
| [ADR-002](ADR-002-provider-contract.md) | Provider 계약 | [제안] |
| [ADR-003](ADR-003-vocal-dataset-consent-policy.md) | Vocal Dataset과 동의 정책 | [제안] |
| [ADR-004](ADR-004-immutable-vocal-asset-lineage.md) | 불변 Vocal Asset 계보 | [제안] |
| [ADR-005](ADR-005-vocal-processing-mix-boundary.md) | Vocal 처리와 DohaMusic Mix 책임 경계 | [제안] |
| [ADR-006](ADR-006-provider-payload-acquisition-authority.md) | Provider Payload Acquisition Authority | [제안] |

결정이 대체되면 기존 ADR을 삭제하지 않고 상태와 새 ADR 링크를 기록합니다.

ADR-006 구현 추적: payload-backed Fake Runtime은 구현했으며, 결정 상태는 제안으로 유지합니다. Production durable Runtime·authentication·rights는 미구현입니다.
