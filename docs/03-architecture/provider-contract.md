# Provider Contract

> 문서 상태: [제안]
> HTTP API: [미구현]

공통 capability는 Capabilities, Create Job, Get Status, Cancel, Retry, Get Result, Get Model Manifest, Health와 Readiness입니다. Job에는 ID, type, status, progress, provider/API/model version, input/output Artifact ID, settings snapshot, retry parent, error와 시간이 포함됩니다.

초기 Local Runner/Subprocess 호환은 `[계획]` 또는 `[Legacy]`로 허용할 수 있지만 장기 계약은 Artifact ID/URI를 사용합니다. Windows 절대 경로는 응답과 Manifest에 노출하지 않습니다.

Provider 간 직접 호출은 금지하며 모든 조정은 DohaMusic을 경유합니다.
