# Provider 계약

> 문서 상태: [구현]
> HTTP API Foundation: [구현]
> Production Provider Runtime: [미구현]
> 공통 명세: `0.1.0` / `draft-baseline`

[DohaStudio 공통 Provider 계약](https://github.com/DohaStudio/.github/blob/main/docs/specifications/04-provider-contract.md)을 기준으로 Capabilities, Create Job, Get Status, Cancel, Retry, Get Result, Get Model Manifest, Health와 Readiness를 구체화합니다. Job에는 ID, type, status, progress, provider/API/model version, input/output Artifact ID, settings snapshot, retry parent, error와 시간이 포함됩니다. 감사와 재현이 필요한 경우 기준 커밋 `1e4b480c8cbd6e51835f8550e685e9b136d8071d`를 사용합니다.

`VocalGenerationJob`, `VoiceConversionJob`, `PitchCorrectionJob`, `TimingCorrectionJob`, `VocalCorrectionJob`, `NoiseReductionJob`, `VocalAnalysisJob`, `EnrollmentProcessingJob`은 독립 계약입니다. DohaVocal 내부에서 한 Job이 다른 Job을 암묵적으로 실행하지 않으며, 저장된 AssetVersion 또는 Artifact를 입력으로 사용합니다. 공통 상태는 [DohaStudio Job 계약](https://github.com/DohaStudio/.github/blob/main/docs/specifications/05-job-contract.md)을 따릅니다.

초기 Local Runner/Subprocess 호환은 `[계획]` 또는 `[Legacy]`로 허용할 수 있지만 장기 계약은 Artifact ID/URI를 사용합니다. Windows 절대 경로는 응답과 Manifest에 노출하지 않습니다.

Provider 간 직접 호출은 금지하며 모든 조정은 DohaMusic을 경유합니다.

## 구현 Surface

| Method | Path | 의미 |
|---|---|---|
| `GET` | `/health` | process 생존 확인 |
| `GET` | `/ready` | Fake Runtime 수락 가능 확인 |
| `GET` | `/v1/capabilities` | 지원 capability와 operation 조회 |
| `POST` | `/v1/jobs` | Job 생성과 idempotent replay |
| `GET` | `/v1/jobs/{job_id}` | Job 상태 조회 |
| `POST` | `/v1/jobs/{job_id}/cancel` | queued/running Job 취소 |
| `POST` | `/v1/jobs/{job_id}/retry` | failed/cancelled Job의 새 retry 생성 |
| `GET` | `/v1/jobs/{job_id}/result` | 성공 Artifact metadata 조회 |
| `GET` | `/v1/model-manifests/{model_manifest_id}` | 불변 Manifest 조회 |

지원 capability는 `vocal_generation`, `voice_conversion`, `vocal_correction`, `vocal_analysis`입니다. Provider interface는 공통 `GetCapabilities`, `CreateJob`, `GetJobStatus`, `CancelJob`, `RetryJob`, `GetResult`, `GetModelManifest`, `Health`, `Readiness` 의미를 유지합니다.

## Idempotency

scope는 `provider_id + capability + project_id + requested_by + idempotency_key`입니다. Fingerprint는 idempotency key를 제외한 전체 정규화 요청을 UTF-8 JSON의 정렬된 key와 고정 separator로 직렬화한 뒤 SHA-256으로 계산합니다. 같은 scope·fingerprint는 기존 Job을 반환하고, 같은 scope의 다른 fingerprint는 `IDEMPOTENCY_CONFLICT`로 거부합니다.

in-memory lock은 단일 Provider process 안의 동시 생성에서 duplicate Job 등록을 막습니다. 여러 process·worker 사이의 idempotency와 상태 동기화는 보장하지 않으며 Production persistence 범위에서 별도로 구현해야 합니다.

저장소 전용 입력은 capability별 `job_input` extension으로 제한합니다. Lyrics·melody DTO를 조직 공통 계약으로 확정하지 않습니다.

## API 측정

2026-08-19 현재 FastAPI/OpenAPI 자동 검증 결과입니다.

| 항목 | 값 |
|---|---:|
| 전체 FastAPI route 수 | 13 |
| DohaVocal API route 수 | 9 |
| OpenAPI path 수 | 9 |
| OpenAPI operation 수 | 9 |
| 중복 operation ID 수 | 0 |

전체 route 수에는 FastAPI의 OpenAPI·문서 route 4개가 포함됩니다. DohaVocal API route와 OpenAPI operation은 위 구현 Surface의 9개입니다.
