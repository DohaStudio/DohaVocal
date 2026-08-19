# 변경 이력

## [미출시]

### 추가

- Python 3.12 `src/dohavocal` Runtime bootstrap과 FastAPI Provider API Foundation
- `VocalGenerationJob`, `VoiceConversionJob`, `VocalCorrectionJob`, `VocalAnalysisJob` 공통 계약
- `queued`·`running`·terminal 상태 전이, 새 Job 기반 retry와 scope별 idempotency
- Model Manifest, 파생 Artifact·AssetVersion 후보와 불변 Vocal lineage metadata
- 실제 모델·오디오·Dataset 없이 동작하는 deterministic metadata-only Fake Provider
- Provider/API/state/retry/idempotency/lineage/security 계약 테스트
- DohaVocal 문서 기반 Architecture와 문서 인덱스
- Vocal Dataset·Consent, immutable lineage, Provider·Mix Boundary 계약
- ADR-001~ADR-005 제안
- Dataset·개인 음성·모델·Artifact Git 보호 정책
- Markdown 제목과 설명을 한국어 공식 문서 언어 기준에 맞게 정리
- Job 상태를 DohaStudio 공통 계약의 `queued`, `running`, `succeeded`, `failed`, `cancelled`로 정렬
- DohaStudio 공통 Provider 계약과 공통 용어 문서 참조 추가
- 공통 명세 `0.1.0` / `draft-baseline`의 안정 기준을 `.github` 저장소 `main`으로 고정
- 여덟 가지 Vocal Job의 독립 실행과 원본 불변·파생 AssetVersion 생성 원칙 명시
- 코드·문서의 Apache License 2.0 적용과 개인 음성·Dataset·모델·생성 결과·동의 증적의 권리 분리 명시

### 미구현

- 실제 AI Singing Voice, Voice Conversion, Vocal Correction 엔진
- Dataset Migration, Training, Evaluation
- User-specific Adapter, Production Runtime과 영속화·실제 Artifact 연동
