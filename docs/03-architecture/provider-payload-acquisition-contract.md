# Provider Payload Acquisition 계약

> 문서 상태: [제안: wire authority] / [미구현: Runtime endpoint·binary payload·Production 인증]
> CURRENT API contract: `0.1.0` metadata-only
> TARGET API contract: `0.2.0` payload acquisition extension
> 관련 결정: [ADR-006](../10-decisions/ADR-006-provider-payload-acquisition-authority.md)

## 1. 목적과 책임

이 계약은 DohaVocal의 성공 Result가 실제 Payload bytes를 어떻게 식별하고 DohaMusic에 제공하는지 정의한다. DohaVocal은 Provider 내부의 stable logical source와 authenticated binary subresource를 소유한다. DohaMusic은 Workspace 권한, acquisition orchestration, 실제 bytes의 checksum·size·media 재검증, trusted staging, Durable Locator와 최종 Workspace Artifact 등록을 소유한다.

다음 identity는 서로 바꿔 쓰지 않는다.

```text
Provider Result candidate identity
!= Provider artifact identity
!= payload source identity
!= payload byte identity
!= DohaMusic Artifact identity
```

이 문서는 wire와 architecture authority만 정의한다. 실제 Payload 생성, binary endpoint, network client, credential integration, persistence, downloader와 DohaMusic ingestion은 모두 `[미구현]`이다.

## 2. Versioned Result variant

CURRENT `0.1.0` Result는 metadata-only다. 기존 DTO·fixture와 의미를 변경하지 않는다.

```text
payload_present=false
payloads field 없음
checksum_scope=metadata_descriptor
actual audio/JSON bytes 없음
```

TARGET `0.2.0`은 명시적으로 협상하는 새 계약 버전이며 다음 discriminated invariant를 사용한다.

```text
payload_present=false  → payloads == []
payload_present=true   → len(payloads) >= 1
```

`payload_present=true`인데 entry가 없거나, `false`인데 entry가 있으면 contract validation failure다. `0.1.0` strict consumer는 `0.2.0` 응답을 자동 수용하지 않으며, Provider는 요청·capability negotiation 없이 새 shape를 보내지 않는다.

## 3. Payload entry와 source identity

TARGET field naming은 기존 snake_case와 flat checksum field 관례를 따른다.

```json
{
  "provider_artifact_id": "opaque-provider-artifact-id",
  "role": "converted_vocal_candidate",
  "source": {
    "kind": "provider_subresource",
    "source_id": "opaque-stable-source-id"
  },
  "checksum_algorithm": "sha256",
  "payload_checksum": "64-lowercase-hex",
  "expected_size_bytes": 1234,
  "expected_media_type": "audio/wav",
  "available_until": "2026-08-26T00:00:00Z"
}
```

Production `0.2.0`의 유일한 source kind는 `provider_subresource`다. `source_id`는 1~200자의 path separator·URI scheme·query·fragment·percent encoding·credential을 포함하지 않는 opaque ASCII identifier다. source identity의 scope는 다음 tuple이다.

```text
(
  provider_id,
  provider_job_id,
  provider_artifact_id,
  payload_role,
  source_id
)
```

`provider_id`는 Result의 `producer_id`와 lineage `provider_id`, `provider_job_id`는 Result의 `run_id`와 lineage `job_id`에서 얻는다. entry는 이 enclosing Result context 밖에서 재사용할 수 없다.

금지 source kind와 값은 다음과 같다.

- `generic_uri`, `signed_url`, `arbitrary_url`, `object_key`, `absolute_local_path`
- `http:`, `https:`, `file:`, `data:` 또는 storage vendor URI
- Windows·POSIX·UNC path, storage root, bucket/container 이름
- Authorization, bearer token, API key, cookie, refresh token, signed query

후속 Fake payload-backed fixture도 로컬 path를 wire에 내보내지 않고 같은 `provider_subresource` shape만 모사해야 한다. 현재 Fake Runtime은 metadata-only이므로 source descriptor를 반환하지 않는다.

## 4. Payload byte expectations

각 entry의 `checksum_algorithm`은 TARGET 첫 버전에서 `sha256`만 허용하고 `payload_checksum`은 lowercase 64자리 hex여야 한다. 이는 Provider expectation이며 최종 Workspace authority가 아니다. DohaMusic은 수신한 bytes에서 SHA-256을 다시 계산하고 mismatch를 fail closed 처리한다.

`expected_size_bytes`는 현재 네 primary role에서 0보다 커야 한다. Provider value와 선택적 HTTP `Content-Length`는 expectation이며 실제 수신 byte count가 authority다. Consumer는 header 유무와 무관하게 role별 configured maximum을 streaming 중 강제해야 한다.

`expected_media_type`은 extension이 아닌 canonical media type이다. TARGET 초기 allowlist는 audio primary role에 `audio/wav`와 `audio/flac`, `vocal_analysis_result`에 `application/json`이다. 선택된 Model Manifest의 `output_formats`와도 일치해야 한다. 현재 metadata-only Fake 값 `audio/x-dohavocal-fake`는 binary acquisition format이 아니다.

checksum과 size는 HTTP transfer decoding 뒤의 exact response entity bytes, media 변환 전을 대상으로 한다. TARGET 첫 버전은 non-identity `Content-Encoding`, partial Range와 Provider-side transcoding을 지원하지 않는다.

```text
metadata_descriptor checksum != payload byte checksum
```

## 5. Cardinality와 role binding

TARGET Result의 `payloads`는 ordered 1:N entry collection이다. replay를 위해 Provider가 canonical order를 고정한다. 현재 capability별 required primary role은 다음과 같다.

| Capability | Required primary role | Kind |
|---|---|---|
| `vocal_generation` | `generated_vocal_candidate` | audio |
| `voice_conversion` | `converted_vocal_candidate` | audio |
| `vocal_correction` | `corrected_vocal_candidate` | audio |
| `vocal_analysis` | `vocal_analysis_result` | JSON |

현재 capability의 payload-backed Result에는 해당 primary role이 정확히 하나 있어야 한다. missing 또는 duplicate primary role, unknown role, duplicate `(provider_artifact_id, role)`, duplicate scoped source identity와 한 source의 복수 role 재사용은 모두 fail closed다. 추가 auxiliary role은 이후 versioned capability vocabulary가 정의하기 전까지 허용하지 않는다. schema는 장래의 명시적 1:N 확장을 막지 않는다.

각 entry는 enclosing Result의 Provider Job, Provider ID, Model Manifest와 lineage에 결속된다. Manifest, lineage 또는 role이 다른 Result로 source descriptor를 복사해 사용할 수 없다.

## 6. Replay와 source lifetime

같은 Provider Job의 `GetResult` replay에서는 다음이 immutable하다.

- payload entry count와 canonical ordering
- Provider artifact identity와 role
- source kind와 source ID
- SHA-256, expected size와 media type
- availability policy

변경은 `PROVIDER_RESULT_REPLAY_CONFLICT`다. credential이나 Provider 내부 storage topology 변화는 Result field가 아니며 replay identity를 바꾸지 않는다. 내부 object relocation이 필요하면 기존 stable source ID가 새 위치를 해석해야 한다. 같은 Result에서 새 source ID로 조용히 교체하지 않는다.

이 불변성은 같은 process 안의 반복 호출뿐 아니라 Provider restart와 DohaMusic reclaim 뒤의 replay에도 적용한다. TARGET Runtime은 Result와 source binding을 durable하게 보존하거나 동일 identity를 결정적으로 복구해야 한다. 현재 in-memory Fake Runtime은 이 production 조건을 충족하지 않으므로 `0.2.0`을 광고할 수 없다.

`available_until`은 stable source lifetime이며 credential expiry가 아니다. timezone-aware UTC timestamp 또는 `null`이다. finite 값이면 그 시점 전까지 권리·삭제 정책이 허용하는 source를 제공해야 한다. `null`이면 explicit deletion, rights revocation 또는 source invalidation 전까지 기술적으로 제공한다는 뜻이다. Provider가 이를 보장할 Runtime persistence와 cleanup acknowledgement는 `[미구현]`이다.

source ID는 credential 또는 access capability가 아니다. source가 존재하더라도 acquisition 요청마다 authentication과 현재 권리 상태를 다시 확인한다.

## 7. Binary acquisition operation

TARGET `0.2.0`은 `GetResult`와 별도의 read-only `GetPayloadContent` operation을 추가한다.

```http
GET /v1/jobs/{job_id}/artifacts/{provider_artifact_id}/payloads/{source_id}
```

path segment는 opaque ID로 encode하며 client가 URL, host, path 또는 query를 전달하지 않는다. Provider는 path의 Job·artifact·source를 저장된 Result entry와 exact하게 대조한다. role은 Result binding에서 얻으며 임의 요청 parameter로 바꾸지 않는다.

성공 응답은 JSON wrapper 없는 binary body다. `Content-Type`은 필수, `Content-Length`는 선택이다. 전송은 streaming과 caller cancellation을 지원해야 하며 consumer가 maximum size를 강제할 수 있어야 한다. redirect는 기본 deny다. endpoint는 fixed configured Provider origin 아래의 origin-relative path만 사용한다.

현재 JSON FastAPI/consumer transport에 binary body를 억지로 넣지 않는다. 후속 Runtime·DohaMusic 구현은 별도 streaming acquisition port를 제공한다. 실제 binary endpoint와 downloader는 이번 계약에 포함되지 않는다.

별도의 `GetPayloadReference` operation은 TARGET 첫 버전에 추가하지 않는다. signed URL이 내부적으로 필요하더라도 Provider 구현 안에서 즉시 해석하고 wire Result, redirect, persistence 또는 log에 노출하지 않는다.

## 8. Capability advertisement와 호환성

CURRENT `0.1.0` capability의 9개 operation과 strict response shape는 유지한다. TARGET `0.2.0`은 `GetPayloadContent`를 포함한 10개 operation과 다음 additive block을 versioned shape로 광고한다.

```json
{
  "payload_acquisition": {
    "supported": true,
    "source_kinds": ["provider_subresource"],
    "operation": "GetPayloadContent"
  }
}
```

Runtime이 binary payload를 실제로 생성·보존·제공하고 authentication·error·replay test를 통과하기 전에는 `0.2.0`이나 `supported=true`를 광고하지 않는다. 현재 Fake Runtime은 계속 `0.1.0`만 광고한다.

## 9. Credential, cancellation과 retry

authentication credential은 Provider transport/runtime configuration이 acquisition 요청 시 주입한다. descriptor, Result, DB, cache key, error, metric과 log에는 저장하지 않는다. credential refresh는 동일 logical source에 새 authentication context를 적용할 뿐 source ID를 바꾸지 않는다.

Provider Job이 이미 `succeeded`면 binary transfer 취소는 요청 중단일 뿐 Result나 Job terminal identity를 변경하지 않는다. acquisition timeout·일시적 network failure는 동일 source에 bounded retry할 수 있으나 자동 `RetryJob` 또는 inference 재실행을 호출하지 않는다.

## 10. 오류 의미

TARGET acquisition pipeline은 최소 다음 의미를 구분한다. Provider endpoint 오류는 기존 안전한 error envelope를 사용하고, DohaMusic이 body 검증 뒤 발견한 integrity mismatch는 동일한 cross-boundary 의미로 매핑한다.

| Error code | 의미 | 기본 retry |
|---|---|---|
| `PROVIDER_RESULT_REPLAY_CONFLICT` | 같은 Job의 immutable Result가 달라짐 | false |
| `PROVIDER_PAYLOAD_UNAVAILABLE` | 약속된 source를 현재 제공할 수 없음 | 명시적 원인에 따라 bounded |
| `PROVIDER_PAYLOAD_EXPIRED` | `available_until` 도달 또는 source lifetime 종료 | false |
| `PROVIDER_PAYLOAD_ACCESS_DENIED` | 인증·권리·삭제 정책이 acquisition을 거부 | false |
| `PROVIDER_PAYLOAD_TRANSFER_FAILED` | timeout 또는 일시적 binary transfer 실패 | true |
| `PAYLOAD_INTEGRITY_MISMATCH` | 수신 bytes가 expected checksum·size와 불일치 | false |

missing primary role, duplicate identity, invalid source, unsupported media와 malformed checksum은 Result validation failure다. 오류는 source secret, raw path, credential, Provider 내부 storage와 response body를 반사하지 않는다. acquisition failure는 Provider inference failure가 아니다.

## 11. Security, rights와 deletion

arbitrary URL이 wire에 없으므로 DohaMusic은 fixed Provider origin만 호출할 수 있다. Production 구현도 HTTPS, origin pinning, redirect deny, encoded path segment, response size ceiling과 cancellation을 유지한다. local development는 configured Provider process가 fixture bytes를 반환할 수 있지만 user-supplied path, absolute path, traversal, symlink/junction escape를 wire input으로 받지 않는다.

DohaVocal은 technical source availability와 invalidation을 소유한다. access revoke, deletion request/application, consent revoke 또는 source invalidation 시 acquisition은 fail closed하고, 이미 시작된 transfer도 중단할 수 있어야 한다. DohaMusic은 요청 전과 최종 ingestion 전 Workspace authorization을 다시 검증한다. opaque source ID 보존 자체도 retention·audit 정책을 따라야 하며 접근 권한을 부여하지 않는다.

## 12. Common Contract와 DohaMusic handoff

고정 Common Provider/Artifact 명세와 현재 Common AI Python schema에는 Provider payload source/acquisition object가 없다. DohaVocal `0.2.0`은 Provider-local versioned extension으로 시작하며 `.github` Common Contract 변경은 이번 범위에서 0건이다. DohaAudio 등 두 번째 실제 소비자가 같은 의미를 요구하면 공통화 여부를 재검토한다.

이 계약이 review·merge된 뒤 DohaMusic은 별도 PR에서 다음을 구현·검증한다.

- `0.2.0` Result DTO와 strict variant parser
- payload entry role·Manifest·lineage·replay trust gate
- binary acquisition port와 safe error mapping
- 실제 byte checksum·size·media 검증과 trusted staging handoff

그 다음에만 `DURABLE_LOCATOR_REQUIRED` 분석을 다시 열어 persistence owner와 schema를 확정한다. 이 문서만으로 Durable Locator, downloader, Completion adapter 또는 Runtime이 구현된 것은 아니다.
