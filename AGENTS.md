# DohaVocal Agent 작업 규칙

이 문서는 저장소 전체에 적용됩니다.

## 작업 흐름

1. 현재 branch, status, 관련 문서와 ADR을 확인합니다.
2. 최신 `develop`에서 목적별 작업 브랜치를 만듭니다.
3. 요청 범위만 변경하고 관련 검증을 실행합니다.
4. 문서와 CHANGELOG를 최신화합니다.
5. 한국어 커밋 후 `develop` 대상 PR을 생성합니다.

## 안전과 경계

- 개인 음성, Dataset, Recording, 실제 Consent 증적, 모델 weight, Adapter, Checkpoint와 생성 음원을 Git에 포함하지 않습니다.
- 동의받지 않은 타인 음성의 생성·변환·사칭 기능을 구현하지 않습니다.
- 원본 보컬은 불변이며 모든 처리는 새 파생 Artifact를 생성합니다.
- Recording Take와 Enrollment Sample은 명시적 승인 없이 Training Dataset이 아닙니다.
- DohaVocal은 다른 Provider를 직접 호출하지 않습니다.
- Workspace, 사용자 권한, 최종 선택, Mix와 Export는 DohaMusic 책임입니다.

## 상태와 근거

구현되지 않은 기능은 `[계획]` 또는 `[미구현]`, 미확인 라이선스·성능은 `[검증 필요]`로 표시합니다. 실제 측정이나 공식 근거가 없는 모델 성능, VRAM, 라이선스와 상업 이용 가능 여부를 단정하지 않습니다.
