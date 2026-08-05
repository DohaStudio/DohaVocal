# Vocal Asset 계보

> 문서 상태: [제안]

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
