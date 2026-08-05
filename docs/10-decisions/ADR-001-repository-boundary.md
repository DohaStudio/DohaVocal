# ADR-001: 저장소 책임 경계

- 상태: [제안]
- 작성일: 2026-08-05
- 관련 PR: bootstrap Draft PR

## 배경

Workspace의 사용자·권리 책임과 Vocal 모델의 Dataset·CUDA·Training·Runtime 책임을 한 저장소에 두면 변경과 보안 경계가 결합됩니다.

## 결정

DohaVocal은 Singing Voice, Voice Conversion, Vocal Correction·Analysis, Dataset, Training, Evaluation, Adapter·Checkpoint·Manifest와 Runtime을 소유합니다. DohaMusic은 사용자, 동의·권한·삭제, Recording Take, Workspace Asset, 후보 선택, Snapshot, Mix와 Export를 소유합니다.

## 선택 이유와 대안

독립 Provider는 의존성·배포·평가를 격리합니다. 모든 기능을 DohaMusic에 유지하는 대안은 초기 단순성은 있으나 책임과 보안이 결합됩니다. 모델별 저장소 대안은 운영 단위가 지나치게 늘어납니다.

## 영향과 단점

Provider 계약·버전 호환과 다중 저장소 운영이 필요합니다. 기존 Dataset·코드는 별도 Migration 승인 전까지 이동하지 않으며 신규 Vocal 기능부터 이 경계를 적용합니다.

## 재검토

독립 Runtime이 기술·운영상 유지 불가능하다는 검증 결과가 있을 때 재검토합니다.
