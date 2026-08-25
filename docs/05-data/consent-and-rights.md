# 동의와 권리

> 문서 상태: [제안]

- Recording Take와 Voice Enrollment Sample은 자동으로 Training Dataset이 아닙니다.
- Training에는 별도의 명시적 승인과 목적별 `training_allowed`가 필요합니다.
- Commercial use와 redistribution은 별도 상태로 관리합니다.
- 동의 철회 시 원본, 파생 Dataset, Adapter·Checkpoint와 Artifact 계보를 조회합니다.
- 삭제 결정과 최종 권한은 DohaMusic이 소유하고 DohaVocal은 기술적 영향 목록을 반환합니다.
- 본인 음성에도 반주·가사·제3자 저작물 권리는 별도로 적용됩니다.
- 실제 동의 증적, 음성 파일과 경로 포함 Manifest는 비공개로 관리합니다.
- payload source가 기술적으로 남아 있어도 access·consent revoke, deletion request/application 또는 source invalidation 뒤 acquisition을 fail closed 합니다. opaque source ID는 접근 capability가 아니며 보존 자체도 retention·audit 정책을 따릅니다.
