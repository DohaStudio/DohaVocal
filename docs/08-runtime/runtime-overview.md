# Runtime 개요

> 문서 상태: [계획]
> Runtime·Provider HTTP API: [미구현]

Runtime은 VocalGeneration, VoiceConversion, PitchCorrection, TimingCorrection, VocalCorrection, NoiseReduction, VocalAnalysis와 EnrollmentProcessing Job을 실행할 계획입니다.

초기 Local Runner/Subprocess 호환은 `[계획]` 또는 `[Legacy]`가 될 수 있으며 장기적으로 versioned 독립 Runtime 계약을 사용합니다. GPU admission과 Provider orchestration은 DohaMusic 책임입니다.
