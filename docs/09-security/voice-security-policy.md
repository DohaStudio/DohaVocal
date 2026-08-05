# 음성 보안 정책

> 문서 상태: [제안]

- 개인 음성과 실제 Recording을 Public Repository에 포함하지 않습니다.
- 원본 Recording과 Training Dataset을 분리하고 명시적 동의를 기록합니다.
- 동의 철회·삭제 요청과 모든 파생 Artifact·Checkpoint 계보를 추적합니다.
- 사용자별 Adapter와 음성 정체성 포함 Checkpoint의 접근을 제한합니다.
- 동의받지 않은 타인 음성 사용과 음성 사칭 목적 사용을 금지합니다.
- 실제 경로와 식별 가능한 파일명을 log에 노출하지 않습니다.
- 저장소의 Apache License 2.0은 코드와 문서에만 적용합니다. Dataset, 개인 음성, Enrollment Sample, Recording Take, 외부 모델·가중치, Checkpoint, Adapter, 생성·변환·보정 결과, 평가 샘플, 동의 증적과 제3자 콘텐츠는 별도 권리와 접근 정책으로 보호합니다.
