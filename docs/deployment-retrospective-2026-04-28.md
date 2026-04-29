# SNS Content Engine 배포 회고 및 다음 프로젝트 배포 체크리스트

- 작성일: 2026-04-28 22:50 KST
- 기준 저장소: `/Users/sonmyeong-gwan/Desktop/sns-content-engine`
- 기준 브랜치: `codex/task-04-smoke-rollout-summary`
- 주요 참고 자료: `docs/first-live-rollout-operations-progress-tracker.md`, `docs/first-live-rollout-operations-roadmap.md`, `docs/single-server-deployment-guide.md`, `README.md`
- 목적: 이번 첫 라이브 배포 준비 중 발생한 문제와 판단을 다음 프로젝트 배포 전에 재사용 가능한 점검 문서로 남긴다.

## 한 줄 요약

이번 배포의 핵심 교훈은 "서버 접근, DNS, 엣지 프록시 소유자, 시크릿, 드라이런, 라이브 승인 경계"를 코드 배포보다 먼저 확인해야 한다는 점이다. 로컬 저장소 검증과 프로덕션 healthcheck는 통과했지만, 서버 접근 경로와 Caddy 포트 소유권 확인이 늦어져 실제 스모크 게이트까지 여러 차례 막혔다.

## 최종 확인된 상태

- 로컬 회귀 테스트와 시크릿 스캔은 통과했다.
- `rollout-summary`가 OpenAI-first provider 경로와 X-only 첫 롤아웃 설정을 시크릿 없이 보여주도록 추가되었다.
- 프로덕션에서 app root, `.env`, config directory, `rollout-summary`, `healthcheck`가 통과했다는 운영자 제공 증거가 기록되었다.
- 기존 Docker Caddy edge가 포트 `80`/`443`을 소유하고 있음이 확인되었다.
- `scripts/single_server_smoke_check.sh`는 프로덕션에서 web service, scheduler service, Docker edge service, rollout summary, healthcheck, loopback health, protected console gate, authenticated console, dry-run publish까지 통과했다.
- Task 04는 별도 프로덕션 `scripts/scan_secrets.sh check` 결과가 남아 있어 완전 완료 전 마지막 확인이 필요하다.
- 라이브 X publish(Task 05)는 아직 실행하지 않았다. `--live`는 별도 명시 승인 전까지 실행 금지다.

## 이번 배포에서 생긴 문제들

| 번호 | 문제 | 증상 또는 기록 | 원인/판단 | 다음 프로젝트 예방책 |
| --- | --- | --- | --- | --- |
| 1 | 로컬 환경을 프로덕션 서버로 착각할 위험 | 로컬에는 `/opt/sns-content-engine`, production `.env`, production config가 없어서 서버 명령이 실행되지 않았다. | Codex 작업 공간과 실제 서버 셸이 분리되어 있었다. | 배포 문서 첫 줄에 `hostname`, `pwd`, `test -d /opt/<app>` 확인을 넣고, 모든 서버 명령 블록에 "서버에서 실행" 라벨을 붙인다. |
| 2 | DNS가 배포 초기에 준비되지 않음 | `sns.gilgop.cloud` 조회가 `NXDOMAIN`으로 실패했고, public `/health`와 `/console` 확인도 불가능했다. | 도메인 또는 로컬 DNS 경로가 아직 준비되지 않았다. | 배포 1일 전 `dig`, `nslookup`, 외부 네트워크 curl을 별도 게이트로 둔다. DNS 미통과 시 서버 내부 healthcheck로만 진행하고 edge 검증은 보류한다. |
| 3 | SSH 접근 경로가 불명확함 | `sns.gilgop.cloud`는 해석되지 않았고, 다른 후보 경로는 host-key 또는 권한 문제로 막혔다. | 배포 전에 접속 호스트명, 사용자, 키, known_hosts, Tailscale 별칭이 정리되지 않았다. | `DEPLOY_HOST`, `DEPLOY_USER`, SSH key, Tailscale hostname, known_hosts 등록 여부를 사전 체크리스트로 관리한다. |
| 4 | 서버 handoff 명령이 로컬에서 실행됨 | Task 03/04 handoff bundle이 현재 세션에서 실행되어 `/opt/sns-content-engine` 부재로 중단되었다. | 복붙 가능한 명령은 있었지만 실행 위치 방어가 부족했다. | 명령 첫 부분에 `echo "RUN THIS ON PRODUCTION"`과 `test "$(hostname)" = ...` 같은 확인을 넣고 실패 시 바로 중단한다. |
| 5 | Caddy 설정은 유효하지만 서비스 재시작 실패 | `caddy validate`는 통과했으나 `systemctl restart caddy`가 `listen tcp :443: bind: address already in use`로 실패했다. | host `caddy.service`가 아니라 기존 Docker Caddy가 포트 `80`/`443`을 소유하고 있었다. | Caddy를 건드리기 전에 `sudo ss -ltnp '( sport = :80 or sport = :443 )'`, `docker ps --format ...`, `systemctl is-active caddy`로 edge owner를 확정한다. |
| 6 | host Caddy와 Docker Caddy 기준이 섞임 | 문서는 기본적으로 `caddy.service`를 기대했지만 실제 edge는 `starterkit-prod-caddy-1` 컨테이너였다. | 서버의 기존 인프라가 저장소 기본 배포 가정과 달랐다. | 프로젝트별로 "edge owner: host systemd / Docker compose / managed proxy"를 배포 전 결정하고 smoke helper의 `SNS_SMOKE_EDGE_SERVICE`를 그에 맞게 override한다. |
| 7 | Docker compose 재기동이 무관한 서비스를 건드림 | Caddy 재생성 과정에서 여러 missing-env warning이 나오고 `minio-init`이 실패했다. | compose project 전체 의존성이 같이 평가되었고 필요한 env 파일이 로드되지 않았다. | compose는 `docker compose --env-file ... config`로 먼저 검증하고, 가능하면 `up -d --no-deps caddy`처럼 영향 범위를 줄인다. |
| 8 | 컨테이너 edge가 host app에 접근하는 경로 필요 | Docker Caddy가 host FastAPI에 접근하려면 `host.docker.internal` 또는 host-gateway 설정이 필요했다. | reverse proxy가 컨테이너 안에서 실행되므로 `127.0.0.1` 의미가 host와 다르다. | Docker edge를 쓰는 프로젝트는 `extra_hosts: ["host.docker.internal:host-gateway"]`와 proxy upstream을 사전에 문서화한다. |
| 9 | edge smoke credential 준비가 별도 필요 | smoke helper는 `SNS_SMOKE_EDGE_USER`, `SNS_SMOKE_EDGE_PASSWORD`가 없으면 protected console 검증을 진행할 수 없다. | Basic Auth 계정은 저장소에 넣을 수 없고, one-shot env로만 주입해야 한다. | smoke 실행 전 credential presence만 확인하고 값을 출력하지 않는 블록을 둔다. 비밀번호는 터미널 히스토리에 남지 않게 주의한다. |
| 10 | 라이브 실행 승인 경계가 계속 강조되어야 함 | 모든 문서와 CLI에서 `publish-due`는 dry-run 기본값이고, `--live`는 별도 승인이 필요했다. | X publish는 외부에 남는 비가역 작업이다. | 배포 문서에 "정확한 live command를 승인받기 전에는 실행 금지" 문장을 반복하고, dry-run 결과를 승인 요청에 같이 첨부한다. |
| 11 | 마지막 보안 게이트가 누락되기 쉬움 | smoke helper는 통과했지만 Task 04 완료 전 production `scripts/scan_secrets.sh check` 결과가 아직 필요하다고 기록되었다. | 서버 스모크 성공과 secret scan은 별도 게이트다. | "스모크 통과 = 완료"로 판단하지 말고, secret scan과 git diff whitespace check를 별도 완료 조건으로 둔다. |

## 다음 프로젝트 배포 전 필수 게이트

### 1. 접속 경로 게이트

```bash
hostname
pwd
test -d /opt/<app-name>
test -f /opt/<app-name>/.env
test -d /opt/<app-name>/config
dig <domain>
curl --fail https://<domain>/health || true
ssh -o BatchMode=yes -o ConnectTimeout=5 <deploy-user>@<deploy-host> 'hostname && pwd'
```

통과 기준:
- 서버 명령이 실제 production host에서 실행되고 있음이 확인된다.
- DNS가 준비되어 있거나, 준비 전이면 edge 검증을 명시적으로 보류한다.
- SSH host, user, key, known_hosts 문제가 없다.

### 2. 로컬 저장소 게이트

```bash
git status --short --branch
./.venv/bin/python -m app.cli version
./.venv/bin/pytest tests/test_config.py tests/test_deploy_assets.py -q
./.venv/bin/pytest tests/test_cli.py tests/test_scheduler.py tests/test_x_publisher.py -q
./.venv/bin/pytest -q
scripts/scan_secrets.sh check
git diff --check
```

통과 기준:
- 테스트 실패가 없거나, 관련 없는 실패라면 근거와 승인 기록이 있다.
- secret scan이 통과한다.
- 배포 전 변경 범위가 설명 가능하다.

### 3. 프로덕션 설정 게이트

```bash
cd /opt/<app-name>
./.venv/bin/sns-engine rollout-summary --config-dir /opt/<app-name>/config
./.venv/bin/sns-engine healthcheck --config-dir /opt/<app-name>/config
```

통과 기준:
- `status=ok`
- 첫 라이브 범위가 의도한 채널만 포함한다.
- credential 값은 출력되지 않고, env var 참조 또는 redacted 형태로만 확인된다.

### 4. Edge owner 게이트

```bash
sudo ss -ltnp '( sport = :80 or sport = :443 )'
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
systemctl is-active caddy || true
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile || true
```

통과 기준:
- 포트 `80`/`443` 소유자가 명확하다.
- host Caddy와 Docker Caddy 중 하나만 주 edge로 결정되어 있다.
- Docker edge라면 host app upstream 경로가 검증되어 있다.

### 5. 드라이런 및 스모크 게이트

```bash
cd /opt/<app-name>
./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/<app-name>/config

export SNS_SMOKE_EDGE_USER=<operator-user>
export SNS_SMOKE_EDGE_PASSWORD='<one-shot-password>'
export SNS_SMOKE_EDGE_SERVICE=docker.service  # Docker edge일 때만 예시
scripts/single_server_smoke_check.sh
```

통과 기준:
- dry-run 출력에 live executor가 나타나지 않는다.
- protected console은 anonymous 요청을 거부하고 인증 요청만 통과한다.
- service, healthcheck, loopback health, authenticated console, dry-run publish가 모두 `status=ok`다.

### 6. 라이브 승인 게이트

라이브 publish는 아래 조건이 모두 맞을 때만 진행한다.

- 로컬 테스트, secret scan, production healthcheck, dry-run, smoke helper가 모두 통과했다.
- dry-run 결과가 예상 계정, 채널, 큐 범위와 일치한다.
- 운영자가 active thread에서 정확한 live command를 명시적으로 승인했다.
- 한 번의 승인으로 한 번의 live command만 실행한다.

승인 대상 명령 예시:

```bash
./.venv/bin/sns-engine scheduler publish-due --config-dir /opt/<app-name>/config --live
```

## 장애별 빠른 대응표

| 상황 | 바로 볼 것 | 다음 행동 |
| --- | --- | --- |
| 도메인이 `NXDOMAIN` | `dig`, DNS provider, nameserver | edge 검증 보류, 서버 내부 healthcheck만 진행 |
| SSH가 막힘 | host, user, key, known_hosts, Tailscale | 접속 경로 확정 전 서버 작업 중단 |
| `/opt/<app>`가 없음 | `hostname`, `pwd`, app root | 로컬/서버 혼동 확인, 실제 서버에서 재실행 |
| `:443 address already in use` | `ss -ltnp`, `docker ps`, `systemctl status caddy` | 기존 edge owner 확인 후 host Caddy 또는 Docker Caddy 중 하나로 통일 |
| Docker compose가 무관한 서비스 실패를 냄 | `docker compose config`, env file 로딩, `--no-deps` 가능 여부 | Caddy 단독 변경 범위로 축소하거나 compose env를 먼저 복구 |
| smoke helper가 edge credential에서 멈춤 | `SNS_SMOKE_EDGE_USER`, `SNS_SMOKE_EDGE_PASSWORD` 존재 여부 | one-shot env로만 주입, 값은 로그에 남기지 않기 |
| dry-run 결과가 예상과 다름 | due queue, channel, account, payload | live 승인 요청 금지, 큐와 config부터 수정 |

## 다음 프로젝트에 바로 복사할 배포 순서

1. 배포 시작 전에 접속 정보, DNS, edge owner, smoke credential 준비 여부를 확인한다.
2. 로컬에서 targeted pytest, full pytest, secret scan, `git diff --check`를 통과시킨다.
3. 서버에서 app root, `.env`, config directory 존재를 확인한다.
4. 서버에서 `rollout-summary`와 `healthcheck`를 실행한다.
5. 포트 `80`/`443` 소유자와 reverse proxy upstream을 확인한다.
6. `scheduler publish-due`를 live flag 없이 실행해 dry-run 결과를 확인한다.
7. `scripts/single_server_smoke_check.sh`를 실행한다.
8. production secret scan 결과를 별도로 기록한다.
9. dry-run과 smoke 결과를 요약해 live 승인 여부를 묻는다.
10. 승인받은 정확한 `--live` 명령을 한 번만 실행한다.
11. publish job 상태, 로그, 외부 게시물 확인 결과를 기록한다.
12. 계속 진행, 일시정지, 재시도, 롤백 중 하나로 다음 결정을 남긴다.

## 이번 프로젝트에서 남은 액션

- Task 04 완료 전 production `scripts/scan_secrets.sh check` 결과를 기록한다.
- Task 05는 아직 실행하지 않는다. X live publish는 dry-run/smoke/secret scan 근거를 요약한 뒤 별도 승인을 받아야 한다.
- Task 06에서는 live publish 이후 job state, 로그, 외부 X 관찰 결과, 다음 운영 결정을 기록한다.
- Docker Caddy를 계속 쓸 경우, 문서와 smoke helper 기본값을 실제 edge owner에 맞게 명확히 보강하는 후속 작업을 고려한다.

## 근거 메모

- `docs/first-live-rollout-operations-progress-tracker.md`에는 2026-04-28 기준 DNS `NXDOMAIN`, SSH 접근 실패, 로컬 `/opt/sns-content-engine` 부재, Caddy `:443` bind 실패, Docker Caddy 소유권, compose missing-env warning, smoke helper 통과가 순서대로 기록되어 있다.
- `scripts/single_server_smoke_check.sh`는 `rollout-summary`, `healthcheck`, loopback `/health`, protected console, authenticated console, dry-run `publish-due`를 모두 확인한다.
- `README.md`, `docs/single-server-deployment-guide.md`, `docs/operator-console-guide.md`는 첫 라이브 롤아웃이 X-only이고 `publish-due`가 dry-run 기본값이며 `--live`는 명시 승인 후에만 실행해야 한다는 경계를 반복한다.
