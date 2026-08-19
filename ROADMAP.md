# DohaVocal 로드맵

> 문서 상태: [계획]

| Phase | 목표 | 상태 |
|---|---|---|
| 1 | Repository Foundation | [계획] |
| 2 | Dataset·Consent Strategy | [계획] |
| 3 | Vocal Asset and Lineage Contract | [계획] |
| 4 | Model Candidate Research | [계획] |
| 5 | Voice Conversion | [계획] |
| 6 | Vocal Correction | [계획] |
| 7 | AI Singing Voice | [계획] |
| 8 | Evaluation | [계획] |
| 9 | Runtime | [계획] |
| 10 | Provider API | [계획] |
| 11 | Stable Release | [계획] |

## 구현된 Foundation

- Runtime Foundation: [구현]
- Provider API Foundation: [구현]
- metadata-only Fake Provider: [구현]
- 공통 Vocal Job lifecycle·idempotency·retry·lineage 계약: [구현]

위 Foundation은 Phase 5~11의 실제 모델, DSP, Training, Evaluation 또는 Production 완료를 의미하지 않습니다.

## 공통 완료 조건

- 책임 경계와 ADR 일치
- Consent·권리·삭제 계보 계약 검증
- Dataset·Artifact·Checkpoint의 Git 외부 보관
- 자동·사람 평가와 재현 가능한 실행 증거
- DohaMusic Provider 계약 호환성
- 테스트, 문서와 CHANGELOG 최신화

이번 bootstrap은 Phase 정의 작업이며 Phase 1 완료를 의미하지 않습니다. 모든 기능은 구현·검증 전까지 `[계획]` 또는 `[미구현]`입니다.
