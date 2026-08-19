# 기능 요구사항

> 문서 상태: [계획]
> Runtime Foundation: FR-010, FR-011의 Fake metadata 계약 [구현]
> 실제 모델·Artifact payload·Consent Gate·Training 요구사항: [미구현]

| ID | 요구사항 |
|---|---|
| FR-001 | 승인된 입력으로 AI Singing Voice Job을 생성한다. |
| FR-002 | 승인된 참조로 Voice Conversion Job을 생성한다. |
| FR-003 | Pitch·Timing·Noise·Breath·Silence 보정 후보를 생성한다. |
| FR-004 | Natural과 Strong Auto-Tune 등 복수 후보를 비파괴 생성한다. |
| FR-005 | Vocal Normalization·De-esser·EQ·Compression을 Asset 자체에 적용한다. |
| FR-006 | 보컬 음정·박자·발음·음질·유사도를 분석한다. |
| FR-007 | Enrollment, Recording, Training Dataset과 생성·처리 결과를 구분한다. |
| FR-008 | Dataset 승인, Training, Fine-tuning과 Checkpoint 계보를 기록한다. |
| FR-009 | Model Manifest와 Evaluation 결과를 연결한다. |
| FR-010 | Job 생성·조회·취소·재시도·결과·Health·Readiness를 제공한다. |
| FR-011 | Artifact ID/URI와 checksum으로 결과를 반환한다. |
| FR-012 | 다른 AI Provider를 직접 호출하지 않는다. |
