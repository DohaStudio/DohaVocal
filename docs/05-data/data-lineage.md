# 데이터 계보

> 문서 상태: [계획]

```text
approved source
→ immutable raw
→ interim derivation
→ reviewed processed item
→ fixed split
→ training run
→ checkpoint / adapter
→ evaluation
→ model manifest
```

각 단계는 이전 ID와 checksum을 참조합니다. 철회·삭제가 발생하면 lineage graph로 영향받는 Dataset version, Training Run, Checkpoint와 모델을 식별하되 자동 삭제 여부는 정책과 사용자 결정을 따릅니다.
