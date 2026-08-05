# ADR-003: Vocal Dataset and Consent Policy

- 상태: [제안]
- 작성일: 2026-08-05
- 관련 PR: bootstrap Draft PR

## 배경

개인 음성은 민감하며 작품 Recording, 음색 등록과 Training 승인 목적이 서로 다릅니다.

## 결정

Recording Take와 Enrollment Sample은 자동으로 Training Dataset이 아닙니다. Training은 별도 명시적 승인, `training_allowed`, commercial/redistribution 상태와 Manifest를 요구합니다. 철회·삭제 시 Dataset, Adapter, Checkpoint와 Artifact 계보를 조회합니다.

## 이유와 대안

목적별 승인은 최소 권한과 사용자의 통제를 보존합니다. 업로드·녹음을 일괄 학습 동의로 보는 대안은 목적 제한과 철회 처리를 위반할 위험이 큽니다.

## 영향

Consent 결정은 DohaMusic, Dataset 기술 계보는 DohaVocal이 관리합니다. 실제 증적과 개인 경로는 private storage에 두며 Public Git에서 제외합니다.

## 재검토

법적 요구, Consent schema 또는 삭제 정책이 변경될 때 재검토합니다.
