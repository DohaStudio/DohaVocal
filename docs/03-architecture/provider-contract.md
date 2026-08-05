# Provider 계약

> 문서 상태: [제안]
> HTTP API: [미구현]
> 공통 명세: `0.1.0` / `draft-baseline`

[DohaStudio 공통 Provider 계약](https://github.com/DohaStudio/.github/blob/main/docs/specifications/04-provider-contract.md)을 기준으로 Capabilities, Create Job, Get Status, Cancel, Retry, Get Result, Get Model Manifest, Health와 Readiness를 구체화합니다. Job에는 ID, type, status, progress, provider/API/model version, input/output Artifact ID, settings snapshot, retry parent, error와 시간이 포함됩니다. 감사와 재현이 필요한 경우 기준 커밋 `1e4b480c8cbd6e51835f8550e685e9b136d8071d`를 사용합니다.

`VocalGenerationJob`, `VoiceConversionJob`, `PitchCorrectionJob`, `TimingCorrectionJob`, `VocalCorrectionJob`, `NoiseReductionJob`, `VocalAnalysisJob`, `EnrollmentProcessingJob`은 독립 계약입니다. DohaVocal 내부에서 한 Job이 다른 Job을 암묵적으로 실행하지 않으며, 저장된 AssetVersion 또는 Artifact를 입력으로 사용합니다. 공통 상태는 [DohaStudio Job 계약](https://github.com/DohaStudio/.github/blob/main/docs/specifications/05-job-contract.md)을 따릅니다.

초기 Local Runner/Subprocess 호환은 `[계획]` 또는 `[Legacy]`로 허용할 수 있지만 장기 계약은 Artifact ID/URI를 사용합니다. Windows 절대 경로는 응답과 Manifest에 노출하지 않습니다.

Provider 간 직접 호출은 금지하며 모든 조정은 DohaMusic을 경유합니다.
