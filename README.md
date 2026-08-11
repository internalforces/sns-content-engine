# SNS Content Engine

뉴스·정보 소스를 수집하고 중복을 제거한 뒤, 채널별 초안을 생성해 사람의 검수와 안전한 발행까지 연결하는 Python 기반 콘텐츠 운영 엔진입니다.

자동 게시량보다 출처 정책, 검수 가능성, 실패 추적, 되돌리기 어려운 외부 발행의 안전성을 우선합니다. 로컬 파이프라인은 항상 `pending_review`에서 멈추며 실발행은 명시적인 `--live` 옵션이 있어야 실행됩니다.

## 핵심 흐름

```mermaid
flowchart LR
    A["RSS · Sitemap · CSV · GDELT"] --> B["정규화 · 중복 제거"]
    B --> C["기사 보강 · 정책 검사"]
    C --> D["브리프 · 채널별 초안"]
    D --> E["사람 검수"]
    E -->|승인·예약| F["Dry-run 또는 실발행"]
    E -->|수정·반려| D
    F --> G["결과 · 오류 · 외부 ID 기록"]
```

- 소스별 `discovery_only`, `reusable`, `restricted` 정책을 수집 시점 데이터로 보존합니다.
- URL, 제목 해시, 최근 콘텐츠 fingerprint, DB 제약을 조합해 중복을 제거합니다.
- OpenAI·Anthropic·Codex-Wrapper 등 생성 경로와 X·Threads 게시자를 설정으로 교체합니다.
- Ghost·LinkedIn과 준비되지 않은 Threads 경로는 수동 발행 인계 작업으로 남깁니다.
- CLI, JSON API, 서버 렌더링 운영 콘솔이 같은 워크플로와 상태 모델을 사용합니다.

## 빠른 실행

Python 3.12–3.13이 필요합니다.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

sns-engine db init --database-url sqlite:///data/sns_content_engine.db
sns-engine healthcheck --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine run-local --config-dir config --database-url sqlite:///data/sns_content_engine.db
sns-engine review list --database-url sqlite:///data/sns_content_engine.db
```

실제 키는 `.env.example`을 참고해 로컬 `.env`나 환경변수에만 저장합니다. 키가 없는 개발·데모 환경에서는 fake provider를 사용합니다.

운영 콘솔:

```bash
uvicorn app.api:create_app --factory --host 127.0.0.1 --port 8000
```

- 콘솔: `http://127.0.0.1:8000/console/`
- 첫 화면은 오래 기다린 초안과 추가 확인이 필요한 항목을 우선하는 검토 홈입니다.
- 승인, 수정, 반려, 예약, 발행 기록, 스케줄러 작업은 기존 서버 검증과 드라이런 기본값을 그대로 사용합니다.
- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `http://127.0.0.1:8000/health`

공개용 샘플 데이터로 구성된 로컬 데모와 동작 영상은 [데모](demo/README.md)에서 확인할 수 있습니다. 실제 계정이나 비밀정보는 포함하지 않습니다.

원격 운영에서는 공유 FastAPI 앱을 `127.0.0.1:8000`에 유지하고 Caddy와 Basic Auth 경계 뒤에 둡니다. 앱을 공개 `0.0.0.0` 주소로 직접 노출하지 않습니다. 배포나 재시작 후에는 다음 점검을 실행하며, 백업과 롤백 순서는 [단일 서버 배포 가이드](docs/single-server-deployment-guide.md)를 따릅니다.

```bash
export SNS_SMOKE_EDGE_USER=operator
read -s SNS_SMOKE_EDGE_PASSWORD
export SNS_SMOKE_EDGE_PASSWORD
scripts/single_server_smoke_check.sh
```

## 품질 게이트

로컬에서 CI와 같은 검사를 실행합니다.

```bash
ruff check .
mypy
pytest -q --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
```

GitHub Actions는 pull request와 `master` push에서 Ruff, 점진적 타입 검사, 전체 테스트, branch coverage 80% 기준을 실행하고 `coverage.xml`을 artifact로 보관합니다. 비밀정보 검사는 별도 workflow로 유지합니다.

## 2–4주 운영 지표

운영 DB에서 동일한 정의로 지표를 산출해 [operations/metrics-history.csv](operations/metrics-history.csv)에 누적합니다.

```bash
python scripts/export_operation_metrics.py \
  --database-url sqlite:///data/sns_content_engine.db \
  --days 28
```

| 지표 | 정의 |
| --- | --- |
| 처리량 | 기간 내 저장 항목 수 ÷ 기간 일수 |
| 중복 제거율 | `(발견 수 - 저장 수) ÷ 발견 수` |
| 승인율 | 승인 수 ÷ `(승인 수 + 반려 수)` |
| 수정률 | 수정 액션 수 ÷ `(승인 수 + 반려 수)` |
| 발행 성공률 | 성공 수 ÷ `(성공 수 + 실패 수)` |

분모가 0인 비율은 0%로 오해하지 않도록 빈 값으로 기록합니다. 매주 같은 요일에 14일 또는 28일 창으로 내보내고, 원본 DB 백업과 함께 결과를 보존하는 방식을 권장합니다.

## 구조

```text
app/
  analytics/    운영 지표 집계
  api/          API 계약·앱 조립·콘솔 라우트·화면 모델
  config/       YAML 스키마와 로더
  connectors/   source / LLM / publisher / TTS 어댑터
  domain/       중복 제거·매칭·브리프 도메인 로직
  scheduler/    슬롯 계획·백필·예약 발행
  services/     추출·생성·검증 서비스
  storage/      SQLAlchemy 모델과 repository
  workflows/    단계별 유스케이스와 검수 전이
config/         운영·예제 설정
deploy/         systemd·Caddy 자산
docs/           사례 분석·운영 회고·배포 가이드
archive/        삭제 검토 중인 과거 tracker·prompt·실행 기록
operations/     반복 측정 가능한 운영 지표 이력
tests/          단위·통합·운영 경계 테스트
```

## 저자와 AI 활용 공개

- **저자·프로젝트 소유자:** `internalforces` (`81242244+internalforces@users.noreply.github.com`)
- **AI 활용:** Codex를 구현 초안, 반복적인 리팩터링, 테스트 케이스 보강, 문서 구조 정리와 변경 검토 보조에 사용했습니다.
- **직접 판단:** 문제 정의, 출처별 이용 정책, 사람 검수 경계, 실발행의 기본 차단, 채널별 자동화 범위, 상태 모델, 운영 지표의 정의와 최종 변경 수용 여부는 프로젝트 소유자가 결정합니다.
- **검증 원칙:** AI가 제안하거나 생성한 코드는 자동 테스트·정적 검사와 실제 운영 검토를 통과한 경우에만 반영합니다. AI는 저자나 의사결정권자로 표기하지 않습니다.

패키지 메타데이터의 저자도 동일한 본인 정보로 맞췄습니다.

## 문서

- [사례 분석](docs/portfolio-case-study.md) — 문제, 설계 결정, 트레이드오프, 검증 근거
- [운영 회고](docs/deployment-retrospective-2026-04-28.md) — 실제 배포에서 얻은 교훈과 다음 게이트
- [배포 가이드](docs/single-server-deployment-guide.md) — 단일 서버 설치, 보안, 백업, 롤백

기존 tracker, roadmap, vibe prompt, 중복 운영 가이드는 [별도 보관소](archive/project-notes/README.md)로 이동했습니다. 2–4주 운영 검증 후 삭제 기준에 따라 정리합니다.
