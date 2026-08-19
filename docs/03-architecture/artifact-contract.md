# Artifact 계약

> 문서 상태: [제안]

Vocal Artifact는 `artifact_id`, `artifact_kind`, `version`, `checksum`, `format`, `size`, `producer`, `source/parent version`, `processing_chain_id`, `model_manifest_id`, `settings_snapshot`, `created_at`을 기록합니다.

예상 URI는 `artifact://vocal/{asset_id}/versions/{version_id}`이며 최종 문법은 Provider API 설계에서 확정합니다. 유일한 원본이나 최종 결과를 Temp에 저장하지 않습니다.

Runtime Foundation의 Fake 결과는 실제 Artifact payload가 아니라 metadata candidate입니다. 호환 필드 `artifact_checksum`에는 canonical metadata descriptor의 SHA-256을 기록하고 `checksum_scope=metadata_descriptor`, `payload_present=false`로 실제 audio payload checksum과 명시적으로 구분합니다. Production Artifact 등록 전에는 이를 실제 payload 무결성 증거로 사용할 수 없습니다.
