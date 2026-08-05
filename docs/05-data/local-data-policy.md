# Local Data Policy

> 문서 상태: [계획]
> Dataset Migration: [미구현]

```text
DohaData/vocal/
├── raw/{singing,speech,enrollment,unclassified}/
├── interim/
├── processed/
├── rejected/
├── manifests/
├── splits/
├── registry/
├── reviews/
├── licenses/
├── consent/
└── private/
```

raw는 불변 원본, interim은 변환·분리·alignment·resampling, processed는 승인된 학습 입력, rejected는 품질·권리 Gate 제외 결과입니다. private에는 실제 절대 경로, 내부 Registry, 비공개 Review와 관리자 backup을 둡니다.

실제 음성과 Dataset은 Public Repository에 포함하지 않습니다. 기존 `DohaMusic-Datasets` 이동은 별도 Migration 승인 후 copy-first와 checksum 검증으로 수행합니다.
