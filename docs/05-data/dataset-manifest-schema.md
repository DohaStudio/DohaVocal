# Dataset Manifest Schema

> 문서 상태: [제안]

Manifest는 Dataset/item ID와 version, source, rights, consent reference, preprocessing, checksum, split, `training_allowed`, `commercial_usage_status`, `redistribution_allowed`, deletion 상태와 lineage를 기록합니다.

`training_allowed` 후보는 `true`, `false`, `pending_review`입니다. 상업 이용 후보는 `research_only`, `commercial_review_pending`, `commercial_approved`, `commercial_rejected`입니다. 실제 경로와 식별 가능한 원본명은 private companion record로 분리합니다.
