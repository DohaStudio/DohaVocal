# DohaVocal 기여 안내

## 브랜치

- `main`: 안정화 브랜치
- `develop`: 일반 작업 통합 대상
- 작업 브랜치: 최신 `develop`에서 생성

## 원칙

- 개인 음성, Recording, Dataset, 동의 증적, Checkpoint와 생성 음원을 커밋하지 않습니다.
- 원본을 덮어쓰지 않고 파생 버전과 계보를 기록합니다.
- Recording Take와 Enrollment Sample을 Training Dataset으로 자동 전환하지 않습니다.
- Provider 간 직접 호출을 추가하지 않습니다.
- 미구현은 `[계획]`·`[미구현]`, 미확인은 `[검증 필요]`로 표시합니다.

PR 대상은 `develop`이며 변경, 검증, 보안·동의 영향, 문서와 후속 작업을 기록합니다.
