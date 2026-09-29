# 변경 이력

## [미출시]

### Payload-backed Fake Runtime Foundation

- 기존 0.1.0 shape를 보존하며 명시적 0.2.0 capability 조회·Job version·전용 Manifest를 추가했다.
- capability별 primary payload descriptor와 process-local WAV/JSON bytes, read-only streaming GetPayloadContent를 구현했다.
- 실제 byte SHA-256·size, exact Job/artifact/source binding, Result replay seal, safe error와 adversarial source 검증을 추가했다.
- ASGI disconnect, repeated acquisition, idempotency·lineage 및 기존 0.1.0 회귀 테스트를 추가했다.
- Production durability·authentication·rights와 실제 AI inference는 포함하지 않는다.

### 추가

- Python 3.12 `src/dohavocal` Runtime bootstrap과 FastAPI Provider API Foundation
- `VocalGenerationJob`, `VoiceConversionJob`, `VocalCorrectionJob`, `VocalAnalysisJob` 공통 계약
- `queued`·`running`·terminal 상태 전이, 새 Job 기반 retry와 scope별 idempotency
- Model Manifest, 파생 Artifact·AssetVersion 후보와 불변 Vocal lineage metadata
- 실제 모델·오디오·Dataset 없이 동작하는 deterministic metadata-only Fake Provider
- Provider/API/state/retry/idempotency/lineage/security 계약 테스트
- 최종 독립 검증에서 path fail-closed 범위, atomic 상태 전이, 연속 lineage와 metadata checksum scope 보강
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
- metadata-only `0.1.0`을 보존하면서 payload-backed Result, stable `provider_subresource`, 1:N payload entry와 별도 binary acquisition operation을 정의한 `0.2.0` TARGET 계약 및 ADR-006 제안
- payload checksum·size·media expectation, replay stability, source lifetime, credential 분리, acquisition 오류·retry·cancellation·권리·SSRF 경계 정의

### 미구현

- 실제 AI Singing Voice, Voice Conversion, Vocal Correction 엔진
- Dataset Migration, Training, Evaluation
- User-specific Adapter, Production Runtime과 영속화·실제 Artifact 연동
- Production payload 생성·인증과 실제 DohaMusic network E2E·Durable Locator 연동

### 수정

- metadata-only Fake Runtime의 `provider_id`를 구현 suffix가 없는 논리 식별자 `dohavocal`로 정합화하고, Fake Model identity `dohavocal.fake-model@0.1.0`과 분리했다.
- Health, Readiness, Capabilities, Job 생성·조회·취소·재시도, Result와 Model Manifest의 Consumer-facing identity 회귀 검증을 추가했다.
