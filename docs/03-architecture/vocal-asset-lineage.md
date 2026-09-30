# Vocal Asset 계보

> 문서 상태: [부분 구현]

## 엔티티 구분

| 엔티티 | 목적 | 소유·승인 |
|---|---|---|
| Voice Enrollment Sample | 음색 등록·변환 참조 | DohaMusic 권리·접근, DohaVocal 기술 처리 |
| Recording Take | 작품의 실제 보컬 녹음 | DohaMusic |
| Vocal Training Dataset | 별도 승인된 학습 데이터 | DohaVocal Dataset, DohaMusic Consent 결정 |
| AI Generated Vocal | 모델이 생성한 가창 | DohaVocal 생성, DohaMusic Asset 선택 |
| Voice Converted Vocal | 음색 변환 파생본 | DohaVocal 생성, DohaMusic Asset 선택 |
| Processed Vocal Asset | 보정 파생본 | DohaVocal 생성 |
| Final Selected Vocal | 작품에 채택된 버전 | DohaMusic |

## 불변 계보

```text
recorded_vocal_raw
├── noise_reduced
├── pitch_corrected
├── timing_corrected
├── natural_tune
├── strong_autotune
├── voice_converted
├── user_adjusted
└── final_vocal
```

원본과 기존 성공 후보를 덮어쓰거나 실패 Job 때문에 삭제하지 않습니다. 모든 파생 결과는 source/parent AssetVersion, processing chain, Provider·Model, 설정, 시각과 checksum을 기록합니다.

0.1.0 Runtime Foundation은 payload를 저장하지 않고 새 `artifact_id`와 `output_asset_version_id` 후보 metadata를 생성합니다. `source_asset_version_id`, `parent_asset_version_id`, `processing_chain_id`, `provider_id`, `model_manifest_id`, immutable settings snapshot, processing type, `job_id`, 생성 시각과 SHA-256 checksum을 기록합니다. 실제 `DohaArtifacts/vocal` 등록과 DohaMusic AssetVersion 생성은 [미구현]이며 DohaMusic 책임 경계를 변경하지 않습니다.

연속 처리에서는 최초 원본을 `source_asset_version_id`, 직전 후보를 `parent_asset_version_id`로 유지하고 동일 `processing_chain_id`를 다음 요청에 전달할 수 있습니다. Fake checksum은 실제 음원이 아니라 `job_id`, capability, source/parent, processing chain, Model Manifest, settings와 processing type으로 구성한 canonical metadata descriptor의 SHA-256입니다.

0.2.0 Fake는 위 lineage를 재작성하지 않고 별도 payload descriptor와 합성 bytes를 선택한 memory 또는 SQLite store에 결속합니다. durable mode는 Job/Result·계보·시각·output ID를 canonical snapshot으로 보존하며 reopen 시 재발급하지 않습니다. acquisition과 transfer retry는 Job·Result·계보를 변경하지 않습니다.
