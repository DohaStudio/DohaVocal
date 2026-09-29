# DohaMusic 연동

> 문서 상태: [계획]

DohaMusic은 사용자 음성 권한, Enrollment/Recording 선택, 보정 후보 표시·최종 선택, Composition Snapshot, 삭제와 상업 이용 결정을 담당합니다. DohaVocal은 승인된 Artifact ID를 입력받아 기술 처리 후 새 Artifact ID와 안전한 Metadata를 반환합니다.

## 처리 경계

| DohaVocal | DohaMusic |
|---|---|
| Pitch·Timing·Beat·Noise·Breath·Silence | 보컬/반주 Gain과 Pan |
| Vocal 전용 Normalize·De-esser·EQ·Compression | 곡 문맥 EQ·Compression |
| Voice Conversion과 후보 생성 | Reverb, Delay, Bus, Mastering, Limiter |
| Vocal 품질 분석 | Mix Version과 WAV·MP3·FLAC Export |

DohaVocal은 DohaAudio·DohaLM을 직접 호출하지 않습니다. DohaAudio와 DohaLM도 DohaVocal을 직접 호출하지 않으며 모든 Provider 연결은 DohaMusic을 경유합니다.

payload-backed TARGET에서는 DohaVocal이 stable source descriptor와 authenticated Provider binary subresource를 소유합니다. DohaMusic은 Result의 role·Manifest·lineage를 검증한 뒤 bytes를 획득하고 checksum·size·media를 재계산하며, trusted staging·Durable Locator와 최종 Artifact commit을 소유합니다. acquisition timeout이나 source expiry는 Provider inference 재실행 또는 자동 `RetryJob`의 근거가 아닙니다. DohaVocal Fake binary endpoint는 구현했습니다. 현재 DohaMusic consumer의 DTO·transport는 read-only 감사했으며 실제 network E2E는 미수행입니다. Provider 계약은 [Provider Payload Acquisition 계약](provider-payload-acquisition-contract.md)을 따릅니다.
