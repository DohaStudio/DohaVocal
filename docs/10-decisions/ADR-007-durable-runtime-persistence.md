# ADR-007: Durable Fake Runtime persistence authority

- 상태: [제안]
- 작성일: 2026-09-30

## 결정

`SQLITE_DURABLE_RUNTIME_STORE`를 선택한다. ADR-006의 Provider-owned Job/Result/source authority를 유지하고 작은 합성 WAV/JSON bytes까지 같은 SQLite DB에 저장한다. metadata와 bytes는 별도 table이며 하나의 transaction authority를 공유한다. filesystem split은 이 범위에서 cross-resource crash gap만 추가하므로 선택하지 않는다. 대용량 실제 모델 output storage는 별도 결정이다.

Fake Provider는 저장소 protocol과 unit of work만 사용한다. 기존 기본 in-memory mode를 유지하고 composition root에서 explicit durable adapter를 주입한다. public API와 capability shape는 변경하지 않는다.

Create와 Retry 전체를 `BEGIN IMMEDIATE` transaction으로 직렬화한다. Job/idempotency, Result, source descriptor, BLOB, succeeded state 및 retry parent가 함께 commit되거나 모두 rollback된다. commit 전 성공 aggregate를 검증한다. journal mode DELETE, synchronous FULL, foreign_keys ON, bounded busy timeout을 사용한다. local filesystem의 SQLite locking을 지원하는 단일 host process 간 동시 접근만 검증하며 network filesystem/multi-node HA는 미지원이다.

명시적으로 생성한 queued/running Job은 reopen 뒤에도 그대로 보존한다. 자동 실행, 성공 전이 또는 bytes 재생성은 없다. 사용자는 기존 CancelJob 후 RetryJob 계약을 사용할 수 있다. 이미 terminal인 Job과 historical Result는 변경하지 않는다. transaction 도중 종료되면 SQLite recovery가 미완료 transaction을 rollback한다.

schema magic `dohavocal.runtime`, version 1을 bootstrap한다. 명시적 initialization 없이 missing DB를 만들지 않는다. 지원하지 않는 version, malformed/변형 schema는 수정 없이 fail closed한다. 기존 process-local state는 non-durable이며 migration하지 않는다.

startup은 DB/schema integrity를 확인하고 records는 domain validation, canonical JSON seal과 relational binding을 읽을 때 확인한다. payload acquisition은 실제 persisted BLOB의 SHA-256/size를 매번 검증한다. seal은 우발적 손상 탐지이며 공격자가 DB와 seal을 함께 변경하는 경우의 인증 수단이 아니다. DB 파일은 trusted operator storage boundary에 둔다.

storage는 trusted configuration의 repository 외부 기존 directory를 사용한다. path를 wire에서 받거나 반환하지 않는다. symlink/reparse ancestor와 DB sidecar를 거부한다. POSIX 신규 DB는 0600, Windows는 operator-controlled directory ACL을 상속한다. OS 수준 storage 교체 공격 및 production authentication/rights는 이번 Foundation의 보장이 아니다.

cleanup/deletion endpoint, scheduler, retention은 추가하지 않는다. committed bytes는 restart로 삭제하지 않는다. BLOB publication rollback은 orphan descriptor/bytes를 남기지 않는다. DELETE journal은 SQLite 자체 복구 대상이며 application payload cleanup 대상이 아니다. durable mode의 `available_until=null`은 restart로 만료되지 않지만 production rights/retention 보장은 아니다.

## 한계

Fake Runtime persistence foundation이며 Production Runtime 완료가 아니다. 실제 inference, user audio, auth/rights, model storage, retention/deletion lifecycle은 미구현이다. DohaMusic은 read-only compatibility reference이며 Provider persistence를 복제하지 않는다.
