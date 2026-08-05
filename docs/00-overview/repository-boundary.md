# 저장소 책임 경계

> 문서 상태: [계획]

| DohaVocal | DohaMusic |
|---|---|
| Singing Voice, Voice Conversion | 사용자·동의·접근 권한·삭제 결정 |
| Pitch/Timing/Noise/Vocal Enhancement | Recording Take와 작품 Asset 관리 |
| Vocal Dataset, Training, Evaluation | 후보 표시·사용자 선택 |
| Adapter, Checkpoint, Manifest, Runtime | Composition Snapshot, Mix, Mastering, Export |

재사용 가능한 Vocal Asset 자체를 교정하면 DohaVocal 책임이고, 특정 반주와 결합해 곡을 완성하면 DohaMusic 책임입니다. DohaVocal은 DohaAudio·DohaLM을 직접 호출하지 않습니다.
