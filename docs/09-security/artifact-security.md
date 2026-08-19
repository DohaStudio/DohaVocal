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
