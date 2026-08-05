# ADR-005: Vocal 처리와 DohaMusic Mix 책임 경계

- 상태: [제안]
- 작성일: 2026-08-05
- 관련 PR: bootstrap Draft PR

## 배경

EQ·Compression 같은 처리는 Vocal 자체 교정과 반주 문맥의 Mix 양쪽에서 사용되어 책임이 중복될 수 있습니다.

## 결정

재사용 가능한 Vocal Asset 자체의 Pitch·Timing·Noise·Breath·Normalize·De-esser·EQ·Compression과 후보 생성은 DohaVocal 책임입니다. 보컬/반주 Gain·Pan, 곡 문맥 EQ·Compression, Reverb·Delay·Bus·Mastering·Limiter·Mix Version과 Export는 DohaMusic 책임입니다.

## 이유와 대안

Asset 재사용성과 작품 문맥을 기준으로 책임을 나누면 동일 Vocal을 여러 Mix에서 사용할 수 있습니다. 모든 처리를 한쪽에 두는 대안은 모델 Runtime 또는 Workspace 책임을 과도하게 확장합니다.

## 영향

처리 설정의 목적과 processing chain을 명시해야 하며 `DohaArtifacts/vocal`과 `DohaArtifacts/music` 결과를 분리합니다.

## 재검토

실시간 공동 DSP graph나 별도 Mixer Provider가 도입될 때 재검토합니다.
