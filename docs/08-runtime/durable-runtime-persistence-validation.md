# Durable Runtime persistence 검증 기록

- 작성일: 2026-09-30
- START develop: `e28320ef26a2dc49eaefdfa62bceea0c8c69e6ed`
- START tree: `f5dc77e8db0d2d2caa051021662b94e7b969d223`
- main: `932466adb435b2a987baacdbefd2361470a2a7fa`
- baseline: 전체 117 passed, exit 0; API 14 / 10 / 10 / 10, duplicate ID 0

## 설계와 authority

[ADR-007](../10-decisions/ADR-007-durable-runtime-persistence.md)의 `SQLITE_DURABLE_RUNTIME_STORE`를 채택했다. Provider-owned Job·Result·source·bytes를 Music에 복제하지 않는다. 작은 Fake WAV/JSON은 SQLite BLOB으로 보관하며 filesystem split과 cross-resource publication gap은 없다. memory mode는 계속 기본값이다. schema migration framework나 dependency upgrade는 도입하지 않았다.

## 실제 schema surface

magic `dohavocal.runtime`, version 1. 파일명은 trusted `--database` 설정으로 선택하며 wire에는 노출하지 않는다. fresh initialization에만 `--initialize-database`가 필요하다. existing empty/malformed/future schema는 거부하고 기존 DB를 destructive migration하지 않는다. 정상 reopen은 동일 schema를 검증한다. missing DB는 재생성하지 않으며 operator가 명시적으로 새로운 DB를 initialize해야 한다. existing process-local runtime state is non-durable and is not migrated.

| Table | Authority | Constraints |
|---|---|---|
| runtime_schema | magic/version | magic primary key, exact one expected row |
| jobs | canonical Job/request, 각각 seal, fingerprint/scope | job_id primary key, scope unique |
| results | canonical Result/lineage/output identity, seal | artifact_id primary key, job_id unique FK jobs |
| sources | ordinal, full source binding, immutable Result snapshot/seal | source_id primary key, artifact_id unique FK results, job_id FK jobs, ordinal=0, binding unique |
| payloads | actual BLOB | source_id primary key/FK sources, content not null |

SQLite가 PK/UNIQUE용 auto-index 9개를 관리하며 별도 application index는 없다. malformed table layout과 extra trigger/view/custom index는 거부한다. payload filesystem layout은 NOT APPLICABLE이다. BLOB은 zeroblob allocation 후 실제 두 부분 쓰기를 사용하며 transaction 안에서만 노출된다.

`foreign_keys=ON`, `journal_mode=DELETE`, `synchronous=FULL`, `busy_timeout=5000ms` (설정 허용 1~30000ms), `BEGIN IMMEDIATE`를 사용한다. 단일 host local SQLite locking에 한해 여러 Runtime/process writer를 직렬화한다. 무한 retry는 없다. SQLite DELETE journal recovery는 DB engine 책임이며 application orphan cleanup 대상이 아니다.

## Transaction과 recovery

Create/Retry 전체를 하나의 unit of work로 수행한다. 성공 전 Result·source descriptor·BLOB·output IDs가 준비되어야 하고 commit 전 aggregate integrity를 검증한다. retry parent도 같은 transaction에 포함한다. 장애 시 Job/idempotency를 포함해 모두 rollback하므로 orphan/partial succeeded record가 없다.

queued/running fixture는 저장한 상태 그대로 reopen한다. 자동 resume/success는 없으며 기존 Cancel/Retry를 사용한다. failed/cancelled/terminal timestamps·error·lineage는 유지한다. 성공 결과는 재생성하지 않는다. Result seal은 canonical JSON과 identity의 SHA-256이며 domain validation 후 읽는다. BLOB은 actual bytes의 size/SHA-256을 읽을 때 검증한다. seal은 operator storage 침해에 대한 cryptographic authentication이 아니다.

startup은 schema/SQLite integrity를 확인한다. 실행 중 storage failure는 readiness 503이고 health는 process 생존 의미다. 모든 connection은 transaction 후 close되며 shutdown은 새 호출을 차단한다. committed bytes는 restart로 삭제하지 않는다. deletion/retention/rights enforcement는 미구현이며 새 endpoint가 없다.

## 실행 근거

- focused `tests/test_durable_runtime.py`: 72 passed, exit 0.
- 기존 API·capability·lifecycle·idempotency/retry·payload·Provider/security: 117 passed, exit 0.
- authoritative 전체 실행: **189 passed, failures 0, errors 0, skips 0, exit 0**, 30.01초.
- 개발 중 추가 테스트에서 누락된 `JobStatus` import로 1 failed / 65 passed가 있었으며 수정 후 focused 66, 이후 최종 72 passed를 확보했다. 이전 실패를 baseline regression으로 취급하지 않는다.
- Python compile, Ruff lint, Ruff format: PASS. diff check: PASS.
- 전체 실행 이후 독립 restart/corruption smoke: **25 passed, 47 deselected, exit 0**. strict UTF-8·relative links/fences·ADR index·secret/private-path·large/runtime-file scan은 issues 0이다. authoritative contradiction 검색은 current 표현을 mode별로 정합화하여 0건이며 historical ADR/validation 기록은 보존한다.

독립 subprocess A가 HTTP TestClient로 생성/조회하고 완전히 종료한 뒤 subprocess B가 같은 DB를 reopen한다. 4 capability × 2 version × graceful/abrupt의 16개 경우에서 Job/Result 전체 JSON 및 bytes가 exact equality다. B에서는 artifact/payload generator를 호출하면 실패하도록 하여 persisted bytes recovery임을 검증한다. same Create는 기존 Job이며 counts 증가 0, changed request는 409다. abrupt committed case는 shutdown callback 없이 `os._exit(0)`로 종료한다. 별도 uncommitted case는 commit 직전 `os._exit(73)` 후 새 instance에서 모든 aggregate count 0을 확인한다. 실제 OS power-loss 내구성 시험은 NOT RUN이다.

12개 failure point: Job insert 전/후, running 전/후, Result insert 전/후, descriptor 전/후, BLOB 부분 쓰기 중/후, succeeded 직전, commit 직전. 매번 새 store reopen에서 jobs/results/sources/payloads 모두 0이다.

손상 matrix: Result seal/JSON, source binding/snapshot, payload length/content, missing BLOB, Job fingerprint/request seal, same-size corrupt BLOB, schema version/magic/layout 및 malformed DB. 오류는 fail closed이며 Job identity는 변경하지 않는다. 교차 process 동일 요청 4개는 같은 Job/Result/bytes와 count 1, 다른 fingerprint의 동시 요청은 한 성공/한 conflict다. 25ms lock timeout failure도 검증했다.

## Consumer와 wire

DohaMusic read-only reference는 PR #196 `fe2f02f0ca68bc3c4e2ccd1e8c64078b7f727379`의 실제 strict client/transport와 fixture다. 현재 develop `7831991239534be5aa7db532676646a1d5e90785`는 PR #195 문서 변경만 추가되어 Consumer code는 동일하다. temporary Music/Provider DB로 4개 capability의 strict 0.1.0/0.2.0 DTO, capability negotiation, GetResult 및 binary acquisition을 검증했다. Music tracked 변경 0. 이는 후속 restart/reclaim/Completion E2E 완료를 뜻하지 않는다.

public API는 baseline과 동일한 14 total routes / 10 API routes / 10 paths / 10 operations / duplicate operation IDs 0이다. 기본 0.1.0은 9 operations, 명시적 0.2.0은 10이다. 0.1.0 Result에 payload field를 추가하지 않는다. source는 기존 opaque provider_subresource이며 DB path, object locator와 credential을 노출하지 않는다.

## 보안과 한계

Git 외부 temporary DB만 사용했다. symlink/reparse path, repository storage, invalid configuration, credential key/Bearer/signed query와 API의 기존 traversal/source attacks를 검증한다. raw DB exceptions를 wire에 전달하지 않는다. POSIX 신규 DB 0600, Windows parent ACL inheritance이며 실제 Windows filesystem에서 실행했다. 임의 사용자 DB/audio/DohaArtifacts/DohaData 접근, model download, GPU, external Provider network 모두 0이다. GitHub API 접근은 저장소 workflow 관리 용도다.

Fake payload이며 실제 AI output이 아니다. Production authentication/rights/writer, 실제 user voice 및 모델 품질, full retention/deletion, network filesystem/distributed HA는 미구현 또는 미검증이다. GitHub Actions는 시작 시 NOT CONFIGURED, branch protection 미설정이며 PR head에서 다시 확인해야 한다. SQLite는 작은 Fake payload foundation이며 대규모 Provider storage 최종 설계가 아니다.

다음 작업은 **DohaMusic ↔ durable DohaVocal restart/reclaim E2E**다. 이번 PR에서 이를 시작하지 않는다. 그 이후 auth/rights/model/worker/retention의 선행 순서는 해당 E2E 결과와 당시 dependency authority로 다시 판단한다.
