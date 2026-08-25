# Runtime 개요

> 문서 상태: [진행 중]
> Runtime·Provider HTTP API Foundation: [구현]
> Production Runtime: [미구현]

Runtime은 VocalGeneration, VoiceConversion, PitchCorrection, TimingCorrection, VocalCorrection, NoiseReduction, VocalAnalysis와 EnrollmentProcessing Job을 실행할 계획입니다.

현재 Python 3.12 Runtime Foundation은 `VocalGenerationJob`, `VoiceConversionJob`, `VocalCorrectionJob`, `VocalAnalysisJob`을 실행하는 공통 lifecycle을 제공합니다. 세부 correction 유형은 `VocalCorrectionJob`의 immutable request snapshot에 기록합니다.

Fake Provider는 deterministic metadata-only 실행체입니다. 기본 요청은 `queued → running → succeeded`로 진행하고 테스트 설정으로 queued/running/failed를 재현합니다. 실제 음원 처리, 모델 load/download, CUDA/GPU, Dataset, Training, subprocess, 외부 HTTP 호출과 Artifact payload 저장은 수행하지 않습니다.

현재 Runtime implementation이 Fake여도 HTTP 응답의 논리 `provider_id`는 `dohavocal`입니다. Fake 특성은 `dohavocal.fake-model@0.1.0` Manifest와 `runtime_environment` metadata로 표현하며 Provider identity에 suffix를 붙이지 않습니다.

초기 Local Runner/Subprocess 호환은 `[계획]` 또는 `[Legacy]`가 될 수 있으며 장기적으로 versioned 독립 Runtime 계약을 사용합니다. GPU admission과 Provider orchestration은 DohaMusic 책임입니다.

Job, idempotency와 Artifact metadata는 명시적인 in-memory adapter에만 저장됩니다. process 재시작 후 보존, 다중 worker 동기화, queue와 DB adapter는 [미구현]입니다.

TARGET `0.2.0` Runtime은 immutable payload-backed Result와 별도 streaming `GetPayloadContent` port를 제공해야 합니다. JSON transport와 binary transport를 분리하고 같은 Result replay에서 source·checksum·size·media를 바꾸지 않습니다. 현재 Fake Runtime에는 actual bytes, binary endpoint, source lifetime persistence와 Production authentication이 없으므로 `0.2.0` 지원을 광고하지 않습니다.
