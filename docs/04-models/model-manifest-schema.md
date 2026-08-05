# Model Manifest Schema

> 문서 상태: [제안]

최소 필드는 다음과 같습니다.

- `provider_id`, `model_id`, `model_version`, `checkpoint_version`
- `model_type`, `capabilities`, `supported_languages`
- `input_formats`, `output_formats`, `api_contract_version`
- `dataset_manifest_id`, `training_run_id`, `evaluation_result_id`
- `license_status`, `commercial_usage_status`
- `voice_identity_scope`, `consent_requirement`
- `recommended_vram`, `runtime_environment`, `artifact_checksum`

`voice_identity_scope` 후보는 `generic`, `user_specific`, `speaker_adapter`, `conversion_reference`입니다. 로컬 절대 경로를 저장하지 않고 실제 검증되지 않은 VRAM과 상업 이용 상태를 단정하지 않습니다.
