# 오류 계약

> 문서 상태: [제안]

오류는 `error_code`, 안전한 message, `retryable`, stage, provider/model/API version과 correlation ID를 포함합니다. Consent/권한 거부, 입력 검증, 모델 준비, 자원 부족, 처리 실패, 취소와 Artifact 저장 실패를 구분합니다.

실제 경로, 개인 음성 Metadata, token, stack trace와 내부 명령은 외부 응답에 포함하지 않습니다. 최종 code 목록은 DohaMusic 계약과 함께 확정합니다.
