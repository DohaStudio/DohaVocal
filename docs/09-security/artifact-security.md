# Artifact 보안

> 문서 상태: [계획]

```text
DohaArtifacts/vocal/
├── checkpoints/
├── models/
├── adapters/
├── generated/
├── converted/
├── pitch/
├── timing/
├── denoised/
├── processed/
├── evaluations/
└── runs/
```

Mix·Export·Preview·Snapshot은 `DohaArtifacts/music`에 두며 Vocal root에 저장하지 않습니다. Artifact는 checksum, lineage, 권한·Consent reference와 삭제 상태를 갖습니다.

```text
DohaTemp/vocal/
├── alignment-cache/
├── pitch-cache/
├── temporary-wav/
├── model-download-temp/
├── processing-chunks/
├── failed-job-temp/
├── test-output/
└── venv/
```

Temp는 재생성 가능해야 하고 유일한 원본 또는 최종 Artifact를 포함할 수 없습니다. 실패·취소 후 임시 파일 정리와 접근 제한을 검증합니다.

Runtime Foundation 입력은 Windows/POSIX/UNC 경로, 상위 경로 traversal과 `file://` URI 및 secret 성격의 key를 fail closed로 거부합니다. `artifact://` 같은 논리 참조와 일반 HTTPS schema URI는 로컬 경로로 오인하지 않습니다.

TARGET Result는 arbitrary URL, signed URL, object key, absolute path와 credential을 반환하지 않고 opaque `provider_subresource`만 사용합니다. binary acquisition은 fixed configured Provider origin의 origin-relative path만 호출하고 redirect를 기본 거부합니다. Fake Runtime은 opaque ID 검증·exact binding·redirect 없는 streaming·cancellation·byte checksum/size 확인을 구현합니다. Consumer의 response size ceiling·media 재검증은 별도 책임이며 Production 권리·삭제 재확인과 authentication은 `[미구현]`입니다.

Fake source ID는 `[A-Za-z0-9][A-Za-z0-9._-]{0,199}`와 `..` 금지 규칙을 사용합니다. Provider가 생성한 UUID 기반 값만 저장하며 user-supplied source를 등록하는 API는 없습니다. Source ID는 credential이 아닙니다. Payload endpoint의 query·percent-encoded path·Range 요청을 거부하며 오류에 요청값이나 내부 위치를 반사하지 않습니다. 테스트 bytes는 합성하며 durable 테스트는 Git 외부 temporary DB만 사용합니다. Git binary fixture로 저장하지 않습니다.

## Durable storage 경계

SQLite 경로는 operator configuration만 받으며 wire에는 포함하지 않는다. 기존 전용 parent directory와 Git 외부 파일을 요구하고 symlink/reparse ancestor·DB sidecar 및 traversal을 거부한다. 신규 POSIX DB는 0600, Windows는 parent ACL 상속이므로 operator가 private directory ACL을 관리한다. 동시에 악의적으로 storage를 교체하는 OS principal까지 격리하는 production sandbox는 아니다.

Canonical record seal은 우발적 corruption 탐지이며 credential/signature가 아니다. startup은 schema/SQLite integrity, read는 domain model·seal·binding, payload read는 실제 BLOB checksum/size를 검증한다. 로그·오류·Result에 path, bytes와 credential을 출력하지 않는다. Production auth/rights와 deletion enforcement는 미구현이다.
