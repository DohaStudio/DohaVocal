# ADR-004: 불변 Vocal Asset 계보

- 상태: [제안]
- 작성일: 2026-08-05
- 관련 PR: bootstrap Draft PR

## 배경

Pitch, Timing, Auto-Tune, Noise와 Voice Conversion은 하나의 원본에서 여러 후보를 만들며 사용자가 비교·되돌리기 할 수 있어야 합니다.

## 결정

원본과 기존 AssetVersion은 덮어쓰지 않습니다. 모든 결과는 새 Artifact와 AssetVersion 후보이며 source/parent, processing chain, Provider·Model, 설정 snapshot, 시각과 checksum을 기록합니다. 실패 Job은 입력과 다른 성공 후보를 삭제하지 않습니다.

## 이유와 대안

불변 계보는 재현, 감사, rollback과 후보 비교를 보장합니다. 제자리 덮어쓰기는 원본 손실과 처리 근거 소실 위험이 있습니다.

## 영향

저장 공간과 lineage 관리 비용이 늘며 retention·삭제 정책이 필요합니다. 최종 작품 버전 선택은 DohaMusic이 담당합니다.

## 재검토

Content-addressed storage나 retention 정책 도입으로 version 표현을 변경해야 할 때 재검토합니다.
