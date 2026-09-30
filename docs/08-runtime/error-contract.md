# 오류 계약

> 문서 상태: [구현]

Foundation 오류는 `error_code`, 안전한 `message`, `retryable`, `stage`, `details_id`를 포함합니다. 입력 검증, 미지원 Provider·contract version, idempotency conflict, 잘못된 상태 전이, 조회 실패와 Fake 처리 실패를 구분합니다. Production 모델 준비·자원 부족·Artifact 저장 오류는 [미구현]입니다.

실제 경로, 개인 음성 Metadata, token, stack trace와 내부 명령은 외부 응답에 포함하지 않습니다. Validation 응답은 사용자 입력값을 반사하지 않고 실패 field 위치만 안전한 `details_id`로 제공합니다.

TARGET payload acquisition은 `PROVIDER_RESULT_REPLAY_CONFLICT`, `PROVIDER_PAYLOAD_UNAVAILABLE`, `PROVIDER_PAYLOAD_EXPIRED`, `PROVIDER_PAYLOAD_ACCESS_DENIED`, `PROVIDER_PAYLOAD_TRANSFER_FAILED`, `PAYLOAD_INTEGRITY_MISMATCH` 의미를 구분합니다. Fake lookup·binding·unavailable·expiry·replay mapping은 구현했습니다. Production 인증·권리 거부 및 network transfer failure integration은 [미구현]입니다. `PAYLOAD_INTEGRITY_MISMATCH`는 Consumer가 수신 bytes 검증 후 판단하는 의미입니다. acquisition failure는 inference failure와 다르며 자동 `RetryJob`을 호출하지 않습니다. 자세한 retryability와 비밀정보 비노출 경계는 [Provider Payload Acquisition 계약](../03-architecture/provider-payload-acquisition-contract.md)을 따릅니다.

## Fake payload endpoint 오류

| HTTP | Code | 의미 | Retry |
|---|---|---|---|
| 400 | `CONTRACT_VERSION_UNSUPPORTED` | 미지원 버전 또는 0.1.0 Job acquisition | false |
| 400 | `PROVIDER_PAYLOAD_INVALID_SOURCE_IDENTITY` | opaque ID·raw path·query 검증 실패 | false |
| 400 | `PROVIDER_PAYLOAD_RANGE_UNSUPPORTED` | partial Range 미지원 | false |
| 404 | `JOB_NOT_FOUND` | Job 없음 | false |
| 409 | `JOB_RESULT_NOT_AVAILABLE` | 성공 Result 없음 | queued/running만 true |
| 404 | `PROVIDER_PAYLOAD_ARTIFACT_MISMATCH` | Job과 artifact 불일치 | false |
| 404 | `PROVIDER_PAYLOAD_SOURCE_NOT_FOUND` | source 없음 | false |
| 404 | `PROVIDER_PAYLOAD_SOURCE_BINDING_MISMATCH` | 다른 binding의 source | false |
| 404 | `PROVIDER_PAYLOAD_UNAVAILABLE` | 등록된 source bytes 없음 | false |
| 410 | `PROVIDER_PAYLOAD_EXPIRED` | finite availability 종료 | false |
| 409 | `PROVIDER_RESULT_REPLAY_CONFLICT` | snapshot·binding·bytes 불변성 위반 | false |

잘못된 URL이 route 자체와 맞지 않으면 framework의 안전한 404를 반환할 수 있습니다. Lookup과 오류는 Job을 수정하지 않습니다. 전송 시작 후 disconnect는 JSON 오류로 바꾸지 않고 transfer를 종료합니다.

## Durable adapter 오류

SQLite mode의 storage open/lock/shutdown failure는 `DURABLE_STORE_UNAVAILABLE` (503), 잘못된 trusted configuration은 `DURABLE_CONFIGURATION_INVALID`, schema magic/version/구조 불일치는 `DURABLE_SCHEMA_INCOMPATIBLE`, DB 구조 손상은 `DURABLE_STORE_CORRUPT`로 거부한다. startup 오류는 Runtime 시작을 중단한다. CLI는 DB 경로와 exception stack을 출력하지 않는다.

persisted canonical snapshot/seal, descriptor, source binding 또는 bytes checksum/size 손상은 기존 `PROVIDER_RESULT_REPLAY_CONFLICT` (409), missing BLOB은 `PROVIDER_PAYLOAD_UNAVAILABLE` (404)다. 같은 key의 다른 fingerprint는 기존 `IDEMPOTENCY_CONFLICT` (409)다. 자동 재생성·Job 변경·무한 retry는 하지 않는다. 모두 안전한 기존 envelope를 사용한다.
