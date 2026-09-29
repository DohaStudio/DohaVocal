# Payload-backed Fake Runtime Foundation 검증

> 측정일: 2026-09-29
> 범위: 0.1.0 호환 및 0.2.0 process-local Fake Runtime
> Production durable Runtime·authentication·rights·실제 AI inference·Training/Evaluation: 미구현

## 기준선

- START 원격 develop: `b0527ea6877f02cdfdb9ada750a285daa1c8ef21`
- START develop tree: `d28d3c4be136b82504c0c894df0fe83c11580b15`
- 원격 main: `932466adb435b2a987baacdbefd2361470a2a7fa`
- 작업 branch: `feature/payload-backed-fake-runtime-foundation`
- 시작 시 로컬 develop은 `59de6c7b50f2e1d28a04f13ad649bf99f5737ec2`, tracked 변경 0건, 기존 미추적 작업·테스트 디렉터리 다수. 기존 파일을 삭제하거나 stage하지 않고 원격 develop에서 작업 branch를 생성했다.
- 시작 및 commit 전 open PR: 0건. commit 전 원격 develop은 START와 동일했다.
- 기준선 전체 suite: 50 passed. Python 3.12.5.

## 구현 경계

기본 capability response와 0.1.0 Job/Result/Manifest는 기존 shape를 유지한다. 0.2.0은 `GET /v1/capabilities?api_contract_version=0.2.0`으로 조회하며 CreateJob body의 version 및 전용 Manifest로 선택한다. GetResult는 저장된 Job version을 따른다. Runtime package/OpenAPI info version 0.2.0과 기본 API contract 0.1.0은 별개다.

Payload entry는 Provider artifact, role, opaque source, SHA-256, positive size, canonical media type, nullable UTC availability를 갖는다. true/false variant는 schema와 runtime에서 payload cardinality를 검증한다. 현재 capability의 primary role은 정확히 하나이며 auxiliary role은 허용하지 않는다.

| Capability | Primary role | Bytes |
|---|---|---|
| vocal_generation | generated_vocal_candidate | 무음 WAV |
| voice_conversion | converted_vocal_candidate | 무음 WAV |
| vocal_correction | corrected_vocal_candidate | 무음 WAV |
| vocal_analysis | vocal_analysis_result | canonical JSON |

WAV는 8 kHz mono PCM16, 800 frames, 1,644 bytes다. SHA-256은 실제 반환 bytes에서 계산하며 metadata descriptor checksum과 분리한다. source ID는 `payload-<UUID>`로 성공 전 한 번 생성한다. Scope는 Provider ID, Job ID, Provider artifact ID, role, source ID의 tuple이다. Source binding과 전체 Result snapshot을 별도 bytes store에서 검증한다.

`GET /v1/jobs/{job_id}/artifacts/{provider_artifact_id}/payloads/{source_id}`는 Service/Provider port를 거쳐 512-byte 이하 chunk를 binary body로 전송한다. Content-Type·실제 Content-Length를 반환하며 JSON/base64 wrapper, redirect, Range, transcoding은 제공하지 않는다. transfer 취소·재시도는 terminal Job, Result와 lineage를 변경하지 않는다.

## 실제 검증

| Gate | 실행/근거 | 결과 |
|---|---|---|
| Focused | `python -m pytest tests/test_payload_runtime.py -q -p no:cacheprovider` | 67 passed |
| 직접 영향 regression | 기존 API/provider/idempotency/state/capability/security 6개 모듈 | 50 passed |
| Full suite | `python -m pytest -q -p no:cacheprovider` 단일 실행 | 117 passed |
| Compile | `python -m compileall -q src tests` | PASS |
| Lint | `python -m ruff check src tests` | PASS |
| Format | `python -m ruff format --check src tests` | 31 files formatted |

기존 테스트는 삭제하지 않았다. 기존 OpenAPI 개수 assertion만 실제 신규 endpoint를 반영해 9에서 10으로 갱신했다. 신규 테스트는 네 capability, 실제 bytes 무결성·크기·media, duplicate/missing/unknown role, source 결속, expiry·unavailable·replay 오류, 동시 idempotency와 계보를 검증한다. 실제 ASGI disconnect를 발생시켜 일부 bytes만 수신한 뒤에도 Job/Result가 동일함을 확인했다.

Adversarial source 21종에는 traversal, Windows/POSIX/UNC, file/http/https/data URI, query/fragment, percent/double encoding, credential 형태, 비ASCII·길이 초과·빈 값과 object path를 포함한다. 정상 opaque ID 6종은 허용한다. 코드와 metadata만 검사했으며 실제 사용자 데이터는 읽지 않았다.

## API surface 실측

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| FastAPI total routes | 13 | 14 |
| DohaVocal API routes | 9 | 10 |
| OpenAPI paths | 9 | 10 |
| OpenAPI operations | 9 | 10 |
| Duplicate operation IDs | 0 | 0 |
| 0.1.0 Provider operations | 9 | 9 |
| 0.2.0 Provider operations | 미지원 | 10 |
| GetPayloadContent | 없음 | 있음 |

기존 OpenAPI와 최종 Runtime을 직접 로드하여 측정했다. operation ID와 광고 목록을 각각 검증했으며 예상 숫자만으로 PASS를 부여하지 않았다.

## DohaMusic read-only 감사

기준 develop: `cda9fa8bd1974d20d431b5efdc80ec024bfd3a21`.

`backend/providers/vocal/contracts.py`, `client.py`, `http_transport.py`, `acquisition.py`, `mapping.py`와 consumer 계약 문서를 읽었다. 실제 0.1.0/0.2.0 × 4 capability의 request·Job·Result·Manifest와 version별 capabilities를 해당 SHA의 strict Consumer DTO로 파싱하여 8개 사례를 통과했다. Source shape, primary role, checksum, size, media, availability와 binary endpoint path/redirect 정책에 wire 충돌은 발견하지 않았다.

WARNING: 현재 Consumer `get_capabilities()`는 version selector를 보내지 않고 mapping 기본값도 0.1.0이다. 따라서 기존 consumer를 그대로 호출하면 0.1.0 호환 경로를 사용한다. 명시적 0.2.0 query 선택을 Consumer에 연결하는 작업과 실제 network E2E는 별도 DohaMusic 작업이다. 이 PR은 Consumer를 수정하지 않는다. DTO 대조는 network E2E 완료를 의미하지 않는다.

## 문서·파일 검사

최종 commit 전 tracked 파일과 이번 신규 파일 81개를 대상으로 strict UTF-8, Markdown relative link·fence, ADR-001~006 numbering/index, secret signature, 개인 절대 경로, 1 MiB 초과 파일 및 audio/model/checkpoint 확장자를 검사했다. 모두 PASS, 발견 0건이다. `git diff --check`도 PASS다. 테스트의 합성 공격 입력은 실제 credential/private path가 아니며 별도로 분류한다. Binary fixture는 저장하지 않는다.

현재 문서의 0.2.0/payload/GetPayloadContent/metadata-only/미구현/Runtime 미구현/binary endpoint/Fake Provider/9·10 operation/Production Runtime/actual bytes/payload_present/provider_subresource를 검색하고 문맥별 검토했다. 현재 구현과 충돌하는 authoritative 표현은 0건이다. 과거 CHANGELOG 기록과 ADR-006 원래 결정은 보존하고 구현 추적만 추가했다.

## 제외·WARNING 및 후속 작업

- Process-local이므로 재시작·다중 worker·reclaim durability는 보장하지 않는다. `available_until=null`은 Fake process 수명 범위다.
- Production authentication·rights·deletion enforcement는 미구현이다. Source ID는 credential이 아니다.
- 실제 사용자 DB/audio, Production Artifact, external Provider network, model download, GPU inference: 모두 0건. GitHub 코드 조회·Git 작업은 개발 metadata 접근이다.
- 실제 DohaMusic network E2E는 NOT RUN. CI 상태는 Draft PR 생성 후 최종 head에서 별도 확인한다.
- Ready, merge, auto-merge, force push, develop/main 직접 push, branch 삭제: 수행하지 않는다.
- BLOCKER: 구현 검증 시점 없음.

후속 순서는 DohaMusic consumer contract E2E, Production Result/source persistence, authentication·rights, 실제 model candidate 선정, 첫 VC inference, 실제 output부터 verified staging·Completion까지 E2E, Correction 확대, Singing Voice 확대, Dataset/Training/Evaluation/Adapter다. 이번 PR에는 포함하지 않는다.
