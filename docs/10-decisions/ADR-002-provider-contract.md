# ADR-002: Provider 계약

- 상태: [제안]
- 작성일: 2026-08-05
- 관련 PR: bootstrap Draft PR

## 배경

장시간 GPU Job, 취소·재시도, Artifact와 Consent 상태를 Provider별 직접 호출로 관리하면 전체 Workflow가 불일치할 수 있습니다.

## 결정

DohaMusic만 DohaVocal을 호출합니다. DohaVocal은 DohaAudio·DohaLM을 직접 호출하지 않습니다. 계약은 capability, Job 생성·상태·취소·재시도·결과, Manifest, Health·Readiness와 API version을 포함하고 Artifact ID/URI를 사용합니다.

## 이유와 대안

단일 Workspace·Job Orchestrator가 사용자 권한, Job과 GPU admission을 일관되게 관리합니다. Provider 직접 호출과 공유 절대 경로 대안은 순환 의존, 배포 결합과 정보 노출을 만듭니다.

## 영향

HTTP endpoint와 schema의 Fake Runtime Foundation은 `[구현]`이며 실제 모델을 실행하는 Production Runtime은 `[미구현]`입니다. Local Runner 호환을 단계적으로 허용하되 외부 절대 경로 계약으로 고정하지 않습니다.

## 재검토

원격 Runtime·scheduler 요구가 확정되어 현재 추상화로 표현할 수 없을 때 재검토합니다.
