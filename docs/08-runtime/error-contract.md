# 오류 계약

> 문서 상태: [구현]

Foundation 오류는 `error_code`, 안전한 `message`, `retryable`, `stage`, `details_id`를 포함합니다. 입력 검증, 미지원 Provider·contract version, idempotency conflict, 잘못된 상태 전이, 조회 실패와 Fake 처리 실패를 구분합니다. Production 모델 준비·자원 부족·Artifact 저장 오류는 [미구현]입니다.

실제 경로, 개인 음성 Metadata, token, stack trace와 내부 명령은 외부 응답에 포함하지 않습니다. Validation 응답은 사용자 입력값을 반사하지 않고 실패 field 위치만 안전한 `details_id`로 제공합니다.
