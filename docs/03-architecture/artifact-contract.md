# Artifact Contract

> 문서 상태: [제안]

Vocal Artifact는 `artifact_id`, `artifact_kind`, `version`, `checksum`, `format`, `size`, `producer`, `source/parent version`, `processing_chain_id`, `model_manifest_id`, `settings_snapshot`, `created_at`을 기록합니다.

예상 URI는 `artifact://vocal/{asset_id}/versions/{version_id}`이며 최종 문법은 Provider API 설계에서 확정합니다. 유일한 원본이나 최종 결과를 Temp에 저장하지 않습니다.
