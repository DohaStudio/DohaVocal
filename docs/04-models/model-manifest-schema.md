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

Foundation은 게시 후 불변인 `ModelManifest` domain model과 Fake Manifest 조회를 구현합니다. Fake Manifest는 `license_status`와 `commercial_usage_status`를 `REVIEW_REQUIRED`, `recommended_vram`을 `null`, 실행 환경을 0.1.0 metadata-only 또는 0.2.0 payload-backed-fake/GPU 미사용으로 명시합니다. 실제 Dataset, Training Run, Evaluation, Checkpoint와 모델 Artifact는 연결하지 않습니다.

Fake Manifest ID는 0.1.0의 `dohavocal.fake-model@0.1.0`과 0.2.0의 `dohavocal.fake-model@0.2.0`입니다. 이는 Fake Model의 identity이며 논리 Provider ID `dohavocal`과 역할이 다릅니다.

Fake Manifest의 `artifact_checksum`은 실제 model/checkpoint payload가 아니라 Fake Manifest 식별 descriptor의 checksum이며 `artifact_checksum_scope=fake_manifest_descriptor`로 표시합니다. Production Model Artifact checksum으로 사용할 수 없습니다.

TARGET payload entry의 `expected_media_type`은 선택된 Manifest의 `output_formats`와 일치해야 하며 Result source는 exact `model_manifest_id` context에 결속됩니다. payload source descriptor를 다른 Manifest 실행에 재사용할 수 없습니다. 0.1.0 Fake Manifest의 `output_formats=[application/json]`는 metadata 응답 형식입니다. 별도 `dohavocal.fake-model@0.2.0` Manifest는 `output_formats=[audio/wav, application/json]` 및 runtime-configured persistence·Production 인증 미구현 상태를 명시합니다. 실제 memory/SQLite 선택은 Runtime configuration의 책임이며 immutable Manifest는 배포 인스턴스 상태가 아닙니다.

## Immutable Manifest publication

같은 `model_manifest_id`는 process, memory/SQLite mode와 관계없이 `created_at`을 포함한 동일 document를 뜻한다. Fake descriptor의 `created_at`은 **MANIFEST_ARTIFACT_CREATION_TIME**으로서 source-controlled descriptor의 최초 develop publication 시각이다. Runtime 시작·discovery·DB registration 시각이 아니다.

| ID | Canonical UTC publication | 역사적 authority |
|---|---|---|
| `dohavocal.fake-model@0.1.0` | `2026-08-19T04:26:36Z` | [PR #4 merge e785ed0](https://github.com/DohaStudio/DohaVocal/commit/e785ed0e0ece8acd09fad6bf29addafa8fd22002) |
| `dohavocal.fake-model@0.2.0` | `2026-09-29T13:32:50Z` | [PR #7 merge e28320e](https://github.com/DohaStudio/DohaVocal/commit/e28320ef26a2dc49eaefdfa62bceea0c8c69e6ed) |

이 기록을 code의 canonical descriptor에 포함하며 startup clock을 고정하거나 정밀도를 낮추지 않는다. 0.2.0 `runtime_environment.persistence=runtime-configured`는 Runtime configuration에서 storage adapter를 선택한다는 고정 특성이다. 실제 인스턴스의 persistence mode는 README 실행 설정에서 확인한다. field/schema를 제거하지 않는다.

`providers/manifests.py`가 유일한 Fake construction authority다. 반환값은 detached copy이며 설정으로 model ID/API version을 바꾸어 같은 ID에 다른 내용을 연결하려 하면 `MANIFEST_CONFIGURATION_CONFLICT`로 거부한다. 기존 default Runtime 설정을 유지하고 0.2.0은 기존 request negotiation으로 선택한다.

향후 model/immutable descriptor content 변경은 새 Manifest identity/version을 요구한다. 이번 수정은 기존 ID의 잘못된 process-dependent metadata를 바로잡는 결함 수정이며 model/payload/checksum 의미를 변경하지 않는다. 기존 SQLite Job/Result의 Manifest ID와 lineage는 재작성하지 않는다. 원래 불변 계약의 복구이므로 새 ADR/schema는 필요하지 않다. [검증 기록](../08-runtime/manifest-restart-invariance-validation.md)을 참조한다.
