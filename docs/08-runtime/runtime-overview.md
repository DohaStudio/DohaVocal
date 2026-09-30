# Runtime 개요

> 문서 상태: [진행 중]
> Runtime·Provider HTTP API Foundation: [구현]
> Production Runtime: [미구현]

Runtime은 VocalGeneration, VoiceConversion, PitchCorrection, TimingCorrection, VocalCorrection, NoiseReduction, VocalAnalysis와 EnrollmentProcessing Job을 실행할 계획입니다.

현재 Python 3.12 Runtime Foundation은 `VocalGenerationJob`, `VoiceConversionJob`, `VocalCorrectionJob`, `VocalAnalysisJob`을 실행하는 공통 lifecycle을 제공합니다. 세부 correction 유형은 `VocalCorrectionJob`의 immutable request snapshot에 기록합니다.

Fake Provider는 기존 metadata-only 0.1.0과 명시적으로 선택한 payload-backed 0.2.0을 제공합니다. 기본 요청은 `queued → running → succeeded`로 진행하고 테스트 설정으로 queued/running/failed를 재현합니다. 실제 음원 처리, 모델 load/download, CUDA/GPU, Dataset, Training, subprocess, 외부 HTTP 호출과 Production Artifact 저장은 수행하지 않습니다. 0.2.0은 합성 무음 WAV와 canonical JSON만 생성하며 memory 또는 explicit SQLite BLOB adapter에 저장합니다.

현재 Runtime implementation이 Fake여도 HTTP 응답의 논리 `provider_id`는 `dohavocal`입니다. Fake 특성은 `dohavocal.fake-model@0.1.0` Manifest와 `runtime_environment` metadata로 표현하며 Provider identity에 suffix를 붙이지 않습니다.

초기 Local Runner/Subprocess 호환은 `[계획]` 또는 `[Legacy]`가 될 수 있으며 장기적으로 versioned 독립 Runtime 계약을 사용합니다. GPU admission과 Provider orchestration은 DohaMusic 책임입니다.

기본 memory mode는 process-local입니다. SQLite mode는 Job·idempotency·Result·source·BLOB을 함께 commit하고 새 process에서 그대로 읽습니다. local multi-process writer 직렬화는 검증했으며 queue/worker와 distributed HA는 [미구현]입니다.

TARGET `0.2.0` Runtime은 immutable payload-backed Result와 별도 streaming `GetPayloadContent` port를 제공해야 합니다. JSON transport와 binary transport를 분리하고 같은 Result replay에서 source·checksum·size·media를 바꾸지 않습니다. Fake Runtime은 actual fixture bytes와 binary endpoint를 구현했으며 `?api_contract_version=0.2.0`에만 개발용 payload 지원을 광고합니다. 기본 조회는 0.1.0입니다. restart persistence foundation은 구현했습니다. Production source lifecycle·rights와 authentication은 [미구현]입니다.

SQLite mode의 schema·transaction·interrupted Job 정책은 [ADR-007](../10-decisions/ADR-007-durable-runtime-persistence.md), 실행 근거는 [durable 검증 기록](durable-runtime-persistence-validation.md)을 따른다. cleanup scheduler/endpoint는 없고 committed bytes는 startup에서 삭제하지 않는다. 기존 process-local state는 migration하지 않는다.
