# 2026-09-09 설치 및 입력 절감 실험

- Headroom 0.37.0: uv 독립 도구 환경에 설치. 실행 파일 C:/Users/xcv54/.local/bin/headroom.exe.
- Task Observer: C:/Users/xcv54/.codex/skills/task-observer 설치. references 7개 포함.
- 현재 데스크톱 채팅의 모델 요청 프록시 연결은 하지 않았다. wrap codex는 새 CLI를 실행한다.
- Task Observer 다음 턴 사용 가능. 자동 활성화 및 장기 절감은 아직 검증하지 않았다.

Headroom 기본 compress(), gpt-4o 토큰 기준, API 추론 호출 없음.
이는 Astra 계정 소비량이 아닌 로컬 입력 토큰 비교다.

| 표본 | 전 | 후 | 절감 |
|---|---:|---:|---:|
| 실제 HANDOFF | 8306 | 8306 | 0% |
| 실제 coverage 소스 | 2920 | 2920 | 0% |
| 합성 반복 로그 1000행 | 10057 | 130 | 98.7% |

합성 로그의 FATAL 문구 및 1265 vs 1264 숫자는 그대로 남았다. 전체 정보 보존이나
동일 답변 품질을 입증한 검사는 아니다. 실제 파일 두 개는 변경 없이 유지됐다.
별도로 o200k_base 기준 전체 인계 8263 vs CURRENT 200 토큰(97.6% 감소)이지만
서로 정보량이 다른 문서이므로 무손실 압축률이 아니다.

재현: Headroom uv 환경 Python으로 tools/benchmark_headroom.py 실행.
결론: 반복 로그에 선택 사용, 수치 원본은 정확히 계산, 현재 채팅 절감률은 미측정.
