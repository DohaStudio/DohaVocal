# Manifest restart invariance 검증

기준 develop: `d0ce053176e7b60be6de6447c3684afb92b7610e`.
범위는 Fake Manifest immutable identity 복원이며 Consumer 및 persistence 구현은 변경하지 않는다.

## 원인과 수정

기존 생성자는 Runtime 시작 시각을 `created_at`으로 기록했다. 같은 Manifest ID의 전체 document가 독립 process마다 달라졌고, 0.2.0의 persistence 값도 Runtime mode에 종속되어 있었다.

`providers/manifests.py`를 단일 정의 authority로 사용한다. `created_at`은 MANIFEST_ARTIFACT_CREATION_TIME, 즉 canonical descriptor가 develop에 최초 게시된 실제 merge 시각이다. [Manifest schema](../04-models/model-manifest-schema.md)에 두 버전의 역사적 commit과 UTC 시각을 기록했다. 임의 epoch, 시각 정밀도 축소, 필드 제외 또는 process clock mocking을 사용하지 않는다. 0.2.0 persistence는 지원하는 설정 경계를 의미하는 `runtime-configured`로 고정한다.

기존 identity 아래 임의 설정으로 다른 descriptor를 만드는 경우 `MANIFEST_CONFIGURATION_CONFLICT`로 fail closed한다. 반환값은 detached deep copy이며 nested dictionary 변경이 canonical document에 전파되지 않는다. 향후 실제 immutable content 변경에는 새 identity/version이 필요하다. 기존 게시 후 불변 계약을 복원하므로 새 ADR 또는 기존 ADR 결정 변경은 필요하지 않다.

## 작업 tree 검증 결과

- focused: Manifest 26 + durable 72 = **98 passed**.
- 직접 영향 regression: **189 passed**.
- full suite: **215 passed**, failures/errors/skips 0, exit 0.
- full suite 이후 독립 memory/SQLite A/B smoke: **2 passed**.
- restart 반복: memory 10쌍 + SQLite 10쌍 = **20쌍**, 실패 0. 각 쌍은 0.1.0과 0.2.0 전체 document를 비교한다.
- A 종료 후 B 시작, 서로 다른 PID, 실제 nanosecond wall clock 순서를 검증한다.
- SQLite 쌍은 기존 Job, Result, source, payload bytes, 같은 Create replay까지 exact equality를 검증한다. Result lineage와 Job의 Manifest ID도 조회 document에 결합한다.
- 별도 localhost Uvicorn A/B 및 기존 DohaMusic strict DTO/client 재현: 수정 전 created_at만 달라 Manifest equality 실패, 수정 후 두 버전 전체 Manifest 및 durable identity chain equality 통과.
- 초기 focused 실행에서 예외 message에 error code를 찾는 테스트 assertion 2건이 실패했다. 구조화된 error code assertion으로 수정한 뒤 위 최종 실행이 통과했다.

기존 PR #8 검증은 Manifest ID 보존을 확인했으나 전체 document equality는 포괄하지 못했다. 과거 보고는 역사 기록으로 유지하고 이번 검증으로 해당 공백을 보완한다.

## API, schema 및 경계

기준선과 수정 tree의 실제 OpenAPI 전체 JSON hash 및 SQLite sqlite_master schema가 동일하다. FastAPI routes 14, DohaVocal API routes 10, OpenAPI paths 10, operations 10, duplicate operation IDs 0. SQLite schema version 1 유지, migration 변경 0.

Python compile, Ruff lint/format, diff whitespace 및 UTF-8/Markdown links/fences/ADR index, secret/private-path/generated DB/audio/model scan을 commit Gate로 확인한다. Draft PR exact head에서 focused/direct/full/20-pair/post-full/static 검증을 별도로 반복한 결과와 원격 Ready/merge authority는 최종 실행 보고에 기록한다.

DohaMusic tracked 변경 0, Consumer workaround 0. 실제 사용자 데이터, 실제 model/GPU, Production Artifact 및 external Provider에 접근하지 않았다. localhost 합성 Fake bytes만 사용했다.

## 문서와 한계

README, CHANGELOG, Provider contract, Manifest schema, Runtime overview를 동기화했다. ROADMAP 및 ADR-007/index는 단계나 결정 변경이 없어 유지한다. 기존 historical validation의 과거 측정치는 수정하지 않는다.

Fake processing이며 실제 AI inference가 아니다. Production authentication/rights, worker daemon 및 cross-system restart/reclaim completion E2E는 이번 범위 밖이다. 다음 작업은 **DohaMusic durable restart/reclaim E2E 재검증**이며 이번 PR에서 시작하지 않는다.
