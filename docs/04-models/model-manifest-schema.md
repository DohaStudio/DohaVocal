# Model Manifest Schema 명세

> 문서 상태: [부분 구현]

최소 필드는 다음과 같습니다.

- `provider_id`, `model_id`, `model_version`, `checkpoint_version`
- `model_type`, `capabilities`, `supported_languages`
- `input_formats`, `output_formats`, `api_contract_version`
- `dataset_manifest_id`, `training_run_id`, `evaluation_result_id`
- `license_status`, `commercial_usage_status`
- `voice_identity_scope`, `consent_requirement`
- `recommended_vram`, `runtime_environment`, `artifact_checksum`

`voice_identity_scope` 후보는 `generic`, `user_specific`, `speaker_adapter`, `conversion_reference`입니다. 로컬 절대 경로를 저장하지 않고 실제 검증되지 않은 VRAM과 상업 이용 상태를 단정하지 않습니다.

Foundation은 게시 후 불변인 `ModelManifest` domain model과 Fake Manifest 조회를 구현합니다. Fake Manifest는 `license_status`와 `commercial_usage_status`를 `REVIEW_REQUIRED`, `recommended_vram`을 `null`, 실행 환경을 metadata-only/GPU 미사용으로 명시합니다. 실제 Dataset, Training Run, Evaluation, Checkpoint와 모델 Artifact는 연결하지 않습니다.

현재 Fake Manifest ID는 `dohavocal.fake-model@0.1.0`입니다. 이는 Fake Model의 identity이며 논리 Provider ID `dohavocal`과 역할이 다릅니다.

Fake Manifest의 `artifact_checksum`은 실제 model/checkpoint payload가 아니라 Fake Manifest 식별 descriptor의 checksum이며 `artifact_checksum_scope=fake_manifest_descriptor`로 표시합니다. Production Model Artifact checksum으로 사용할 수 없습니다.
