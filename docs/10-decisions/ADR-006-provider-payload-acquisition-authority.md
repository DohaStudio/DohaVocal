# ADR-006: Provider Payload Acquisition Authority

- 상태: [제안]
- 작성일: 2026-08-25
- 관련 문서: [Provider Payload Acquisition 계약](../03-architecture/provider-payload-acquisition-contract.md)

## 배경

현재 DohaVocal `0.1.0` Result는 `payload_present=false`, `checksum_scope=metadata_descriptor`인 metadata candidate만 반환한다. `artifact_id`는 logical Result identity이며 실제 bytes를 찾는 source, byte checksum 또는 DohaMusic Artifact identity가 아니다. DohaMusic의 production payload reconciliation과 Durable Locator 설계에는 replay 가능한 upstream source authority가 먼저 필요하다.

## 결정

1. CURRENT `0.1.0` metadata-only Result와 strict consumer 호환성을 유지한다.
2. TARGET `0.2.0`은 metadata-only와 payload-backed Result variant를 version으로 구분한다.
3. payload-backed Result는 ordered 1:N payload entry와 stable non-secret `provider_subresource` source를 반환한다.
4. source identity는 Provider, Job, Provider artifact, role과 opaque source ID에 결속한다.
5. Provider expectation으로 SHA-256, positive size, allowed media type과 source lifetime을 반환한다.
6. 실제 bytes는 fixed Provider origin의 별도 read-only `GetPayloadContent` subresource로 제공한다.
7. credential, signed URL과 storage path는 Result identity나 persistence에 포함하지 않는다.
8. replay field 변경은 conflict이며 credential refresh와 source identity 변경을 분리한다.
9. acquisition failure는 inference failure가 아니며 자동 `RetryJob`을 호출하지 않는다.
10. 권리 철회·삭제·source invalidation 시 acquisition을 fail closed 한다.

## 이유와 대안

Provider-owned subresource는 arbitrary URL과 raw path를 제거하면서 Provider가 storage topology와 인증을 캡슐화한다. signed URL은 short-lived credential이므로 durable identity 대안에서 제외했다. `GetPayloadReference` metadata operation은 Result가 stable descriptor를 이미 제공하므로 첫 버전에는 추가하지 않는다. 1:N entry는 현재 한 primary output을 엄격히 검증하면서 향후 명시적인 auxiliary output을 새 version으로 확장할 수 있다.

## 영향

DohaVocal이 source와 binary availability를, DohaMusic이 Workspace authorization·byte verification·staging·Durable Locator·Artifact commit을 소유한다. Common Contract 변경은 필요하지 않다. Runtime endpoint, binary generation, persistence, Production authentication과 DohaMusic consumer는 후속 구현이다. 이 ADR의 병합 뒤에만 DohaMusic이 consumer extension을 진행하고 `DURABLE_LOCATOR_REQUIRED`를 재분석할 수 있다.

## 재검토

두 개 이상의 Provider가 동일한 source/acquisition 의미를 실제로 소비하거나, fixed Provider subresource로 표현할 수 없는 배포 요구가 검증되면 Common Contract 승격과 source kind 확장을 재검토한다.

## 구현 상태 (2026-09-29)

기존 결정은 유지한다. 0.1.0 호환과 명시적 0.2.0 payload-backed Fake Runtime, deterministic WAV/JSON, binary endpoint와 단일 process replay 검증을 구현했다. 이는 개발용 Foundation이며 restart/reclaim durability, Production authentication·rights 및 실제 AI inference는 미구현이다. 원래 영향 절의 후속 구현 항목 중 Fake 부분만 완료했으며 Production 요건을 완화하지 않는다.
