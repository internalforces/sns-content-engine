# Review-First Operator Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the card-heavy operator console with the approved review-first editorial workspace while preserving every server-rendered workflow and safety guardrail.

**Architecture:** Keep FastAPI and Jinja as the source of complete, functional HTML. Add one focused home view-model module, reusable Jinja macros, a rewritten token-based stylesheet, and one progressively enhanced JavaScript file that initializes GSAP only on supported desktop review-detail pages. Existing GET/POST routes, database models, review transitions, query-string context, and dry-run defaults remain authoritative.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, semantic HTML, CSS custom properties, vanilla JavaScript, GSAP 3.13.x, ScrollTrigger, pytest.

## Global Constraints

- Preserve `python >=3.12,<3.14`, FastAPI/Jinja server rendering, and the absence of a React/SPA build chain.
- Do not add database migrations, new state transitions, publishing providers, authentication, auto-approval, or automatic live publishing.
- Preserve `config_dir` and `database_url` across all console navigation and detail links.
- Preserve mandatory manual review and the unchecked browser live-publish checkbox.
- Use only Ink `#151713`, Warm Ivory `#F2F0E9`, Sage `#738274`, Sage Tint `#DFE4DC`, and Neutral Rule `#CBC9C0` as page colors.
- Use `font-family: "Geist", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif`; font failure must leave readable system text.
- Use `font-size: clamp(3rem, 5vw, 5.5rem)` and a wide H1 column; target two desktop lines and at most three mobile lines.
- Remove numbered meta labels such as `작업 01`, `SECTION 01`, and `QUESTION 05` from rendered UI.
- Keep the full shell at `overflow-x: hidden; width: 100%; max-width: 100%`; verify 375px, 768px, and 1440px.
- Every link and form must work without JavaScript; GSAP is progressive enhancement only.
- Disable pinning, stacking, marquee, and transform motion under `prefers-reduced-motion: reduce`.
- Do not add emojis to code, comments, copy, or documentation.
- Follow TDD and commit after each independently testable task.

## File Structure

**Create:**

- `app/api/console_view_home.py`: pure review-home display-model builders.
- `app/api/templates/console/_macros.html`: shared page intro, summary, and empty-state markup.
- `app/api/static/console.js`: defensive GSAP/ScrollTrigger enhancement.

**Modify:**

- `app/api/console.py`: load home review and run data.
- `app/api/console_view_common.py`: static asset URLs and concise navigation.
- `app/api/console_views.py`: re-export home builders.
- `app/api/templates/base.html`: semantic rail/mobile shell.
- `app/api/templates/console/*.html`: approved page hierarchy across all console screens.
- `app/api/static/console.css`: complete visual and responsive rewrite.
- `tests/test_console.py`: view contracts, semantic hooks, assets, and regressions.
- `README.md`: describe the review-first entry point.

---

### Task 1: Build the Home Display Contract

**Files:**
- Create: `app/api/console_view_home.py`
- Modify: `app/api/console_views.py`
- Modify: `app/api/console.py:87-125`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes: `PendingReviewDraftsResult.drafts`, `PipelineRunHistoryResult.runs`, `Request.url_for()`, `_append_query_params()`.
- Produces: `_format_wait_duration(created_at: datetime, *, now: datetime) -> str`.
- Produces: `_build_home_review_rows(request, query_params, rows, *, now, limit=3) -> list[dict[str, str | bool]]`.
- Produces: `_build_home_summary(rows, latest_run) -> list[dict[str, str]]`.
- Produces template keys `home_review_rows`, `home_summary`, `home_first_review_href`, `home_queue_href`, `home_scheduler_href`, `home_data_error`.

- [ ] **Step 1: Write failing formatter and home route tests**

```python
from datetime import timedelta

from app.api.console_view_home import _format_wait_duration
from app.workflows import PipelineRunHistoryResult


def test_format_wait_duration_uses_operator_friendly_units() -> None:
    now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
    assert _format_wait_duration(now - timedelta(minutes=37), now=now) == "37분"
    assert _format_wait_duration(now - timedelta(hours=2, minutes=14), now=now) == "2시간 14분"
    assert _format_wait_duration(now - timedelta(days=2, hours=3), now=now) == "2일 3시간"


def test_console_home_prioritizes_oldest_review_and_sensitive_copy() -> None:
    now = datetime.now(timezone.utc)

    def list_pending(*, database_url: str | None = None) -> PendingReviewDraftsResult:
        return PendingReviewDraftsResult(drafts=(
            PendingReviewDraft(
                draft_id=42, account_key="korea_news", channel="x", variant_index=0,
                created_at=now - timedelta(hours=2),
                title="Defense ministry reports missile launch",
                body="Officials said security agencies are reviewing the launch.",
            ),
            PendingReviewDraft(
                draft_id=43, account_key="japan_news", channel="ghost", variant_index=0,
                created_at=now - timedelta(hours=1),
                title="Manufacturing investment update", body="A sourced industry summary.",
            ),
        ))

    client = TestClient(create_app(
        pending_review_drafts_lister=list_pending,
        pipeline_runs_lister=lambda **_: PipelineRunHistoryResult(runs=()),
    ))
    response = client.get("/console/", params={"database_url": "sqlite:///demo.db"})
    assert response.status_code == 200
    assert response.text.index("Defense ministry") < response.text.index("Manufacturing")
    assert "추가 확인 필요" in response.text
    assert "/console/reviews/42?database_url=" in response.text
```

- [ ] **Step 2: Run tests and verify failure**

```bash
pytest tests/test_console.py::test_format_wait_duration_uses_operator_friendly_units tests/test_console.py::test_console_home_prioritizes_oldest_review_and_sensitive_copy -v
```

Expected: FAIL because `console_view_home` and review-first home context do not exist.

- [ ] **Step 3: Implement the pure builders**

```python
"""Display models for the review-first console home."""

from datetime import datetime
from fastapi import Request
from app.api.console_view_common import _append_query_params, _humanize_label
from app.services.prompt_renderer import build_domain_sensitivity


def _format_wait_duration(created_at: datetime, *, now: datetime) -> str:
    minutes = max(0, int((now - created_at).total_seconds()) // 60)
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}시간 {minutes % 60}분"
    return f"{hours // 24}일 {hours % 24}시간"


def _build_home_review_rows(request: Request, query_params, rows, *, now, limit=3):
    items = []
    for row in sorted(rows, key=lambda item: item.created_at)[:limit]:
        sensitivity = build_domain_sensitivity(title=row.title, summary=row.body, tags=())
        items.append({
            "draft_id": str(row.draft_id),
            "title": row.title,
            "channel": _humanize_label(row.channel),
            "account_key": row.account_key,
            "review_flag": (
                f"{_humanize_label(sensitivity.domain)} 추가 확인"
                if sensitivity.is_high_risk else "일반 검토"
            ),
            "needs_attention": sensitivity.is_high_risk,
            "wait_duration": _format_wait_duration(row.created_at, now=now),
            "detail_href": _append_query_params(
                str(request.url_for("console_review_detail", draft_id=row.draft_id)),
                query_params,
            ),
        })
    return items


def _build_home_summary(rows, latest_run):
    sensitive_count = sum(
        build_domain_sensitivity(title=row.title, summary=row.body, tags=()).is_high_risk
        for row in rows
    )
    return [
        {"label": "검토 대기", "value": str(len(rows))},
        {"label": "추가 확인 필요", "value": str(sensitive_count)},
        {
            "label": "최근 파이프라인",
            "value": _humanize_label(latest_run.status) if latest_run else "이력 없음",
        },
    ]
```

- [ ] **Step 4: Wire the home route and schema-error fallback**

```python
try:
    pending_result = request.app.state.console_pending_review_drafts_lister(
        database_url=database_url
    )
    runs_result = request.app.state.console_pipeline_runs_lister(
        database_url=database_url, limit=1
    )
except DatabaseSchemaError as exc:
    pending_result = runs_result = None
    home_data_error = str(exc)
else:
    home_data_error = None
```

Compute `now = datetime.now(timezone.utc)`, preserve current query parameters in all home links, re-export the builders from `console_views.py`, and remove obsolete `console_sections`.

- [ ] **Step 5: Run focused regressions**

```bash
pytest tests/test_console.py::test_format_wait_duration_uses_operator_friendly_units tests/test_console.py::test_console_home_prioritizes_oldest_review_and_sensitive_copy tests/test_console.py::test_console_shell_root_redirects_to_canonical_landing -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/api/console_view_home.py app/api/console_views.py app/api/console.py tests/test_console.py
git commit -m "feat: add review-first console home data"
```

---

### Task 2: Replace the Shared Shell and Visual Tokens

**Files:**
- Create: `app/api/templates/console/_macros.html`
- Modify: `app/api/console_view_common.py:26-101`
- Modify: `app/api/templates/base.html`
- Modify: `app/api/static/console.css`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes: `console_nav_items`, `operator_context`, `page_title`, `page_description`.
- Produces: `console_asset_js_url`, six concise nav labels, and `.console-shell-grid`, `.console-rail`, `.console-workspace`, `.page-intro`, `.data-list`, `.summary-strip`.
- Produces macros `page_intro(title, description, action_href=None, action_label=None)`, `summary_item(item)`, and `empty_state(title, copy, href=None, label=None)`.

- [ ] **Step 1: Write failing shell and palette tests**

```python
def _build_empty_console_client() -> TestClient:
    return TestClient(create_app(
        pending_review_drafts_lister=lambda **_: PendingReviewDraftsResult(drafts=()),
        pipeline_runs_lister=lambda **_: PipelineRunHistoryResult(runs=()),
    ))


def test_console_shell_uses_review_first_landmarks() -> None:
    response = _build_empty_console_client().get("/console/")
    assert 'class="console-rail"' in response.text
    assert 'aria-label="운영 콘솔 탐색"' in response.text
    assert 'class="console-workspace"' in response.text
    assert "작업 01" not in response.text


def test_console_stylesheet_exposes_minimal_tokens() -> None:
    response = TestClient(create_app()).get("/console/static/console.css")
    assert "--ink: #151713" in response.text
    assert "--ivory: #f2f0e9" in response.text
    assert "--sage: #738274" in response.text
    assert "overflow-x: hidden" in response.text
    assert "prefers-reduced-motion: reduce" in response.text
```

- [ ] **Step 2: Run and verify failure**

```bash
pytest tests/test_console.py::test_console_shell_uses_review_first_landmarks tests/test_console.py::test_console_stylesheet_exposes_minimal_tokens -v
```

Expected: FAIL on old shell classes and orange palette.

- [ ] **Step 3: Create macros and semantic base shell**

```html
<body class="console-shell">
  <main class="console-shell-grid">
    <aside class="console-rail" aria-label="운영 콘솔 탐색">
      <a class="console-wordmark" href="{{ console_nav_items[0].href }}">SNS CONTENT<br>ENGINE</a>
      <nav class="console-nav">
        {% for item in console_nav_items %}
          <a class="console-nav-link{% if item.active %} is-active{% endif %}"
             href="{{ item.href }}"{% if item.active %} aria-current="page"{% endif %}>
            {{ item.label }}
          </a>
        {% endfor %}
      </nav>
      <div class="console-safety-state">
        <span>기본 발행은 드라이런</span><span>수동 검토 필수</span>
      </div>
    </aside>
    <section class="console-workspace">
      <header class="console-utility">
        <span>{{ page_title }}</span><span>{{ operator_context.config_dir }}</span>
      </header>
      {% block content %}{% endblock %}
    </section>
  </main>
</body>
```

Add a native `<details class="console-mobile-nav">` before the rail so mobile navigation works without JavaScript.

```html
<details class="console-mobile-nav">
  <summary>운영 메뉴</summary>
  <nav aria-label="모바일 운영 콘솔 탐색">
    {% for item in console_nav_items %}
      <a href="{{ item.href }}"{% if item.active %} aria-current="page"{% endif %}>
        {{ item.label }}
      </a>
    {% endfor %}
  </nav>
</details>
```

- [ ] **Step 4: Rewrite the stylesheet from tokens**

```css
:root {
  --ink: #151713;
  --ivory: #f2f0e9;
  --sage: #738274;
  --sage-tint: #dfe4dc;
  --rule: #cbc9c0;
  --muted: #666b64;
  --rail-width: 13.5rem;
}
html, body { width: 100%; max-width: 100%; overflow-x: hidden; }
body {
  margin: 0; color: var(--ink); background: var(--ivory);
  font-family: "Geist", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
}
.console-shell-grid {
  display: grid; grid-template-columns: var(--rail-width) minmax(0, 1fr);
  min-height: 100vh;
}
:focus-visible { outline: 3px solid var(--sage); outline-offset: 3px; }
.console-button, .console-input, .console-nav-link { min-height: 44px; }
@media (max-width: 900px) {
  .console-shell-grid { display: block; }
  .console-rail { display: none; }
  .console-mobile-nav { display: block; }
}
@media (max-width: 600px) {
  .data-list-row { display: grid; grid-template-columns: 1fr; }
  .data-list-row [data-label]::before { content: attr(data-label); display: block; }
}
```

Add 44px controls, ruled lists, inputs, feedback, desktop rail, and responsive mobile details. At `max-width: 900px`, hide the rail and show mobile navigation. At `max-width: 600px`, stack `.data-list-row` values with visible labels.

- [ ] **Step 5: Shorten navigation without removing routes**

Use these six labels and add the JavaScript asset URL:

```python
nav_specs = (
    ("검토 홈", "console_home", "home"),
    ("전체 검토 큐", "console_pending_review", "pending_review"),
    ("실행", "console_dashboard", "dashboard"),
    ("아티클", "console_articles", "articles"),
    ("발행", "console_publish_jobs", "publish_jobs"),
    ("스케줄러", "console_scheduler", "scheduler"),
)
context["console_asset_js_url"] = str(
    request.url_for("console_static", path="/console.js")
)
```

- [ ] **Step 6: Run console regression tests**

```bash
pytest tests/test_console.py -q
```

Expected: PASS after updating only assertions tied to deliberately removed labels/markup.

- [ ] **Step 7: Commit**

```bash
git add app/api/console_view_common.py app/api/templates/base.html app/api/templates/console/_macros.html app/api/static/console.css tests/test_console.py
git commit -m "feat: replace operator console shell"
```

---

### Task 3: Implement the Review-First Home and Full Queue

**Files:**
- Modify: `app/api/templates/console/index.html`
- Modify: `app/api/templates/console/pending_review.html`
- Modify: `app/api/static/console.css`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes: `home_*`, `pending_review_rows`, `pending_review_metrics`.
- Produces: `.review-hero`, `.priority-queue`, `.priority-row`, `.queue-list`, `.queue-row-link`, mobile `data-label` values.

- [ ] **Step 1: Write failing hierarchy tests**

```python
def _build_console_client_with_two_pending_drafts() -> TestClient:
    now = datetime.now(timezone.utc)
    drafts = (
        PendingReviewDraft(
            draft_id=42, account_key="korea_news", channel="x", variant_index=0,
            created_at=now - timedelta(hours=2), title="Korea policy briefing", body="Draft A",
        ),
        PendingReviewDraft(
            draft_id=43, account_key="japan_news", channel="ghost", variant_index=0,
            created_at=now - timedelta(hours=1), title="Japan industry update", body="Draft B",
        ),
    )
    return TestClient(create_app(
        pending_review_drafts_lister=lambda **_: PendingReviewDraftsResult(drafts=drafts),
        pipeline_runs_lister=lambda **_: PipelineRunHistoryResult(runs=()),
    ))


def test_console_home_renders_single_primary_review_action() -> None:
    response = _build_console_client_with_two_pending_drafts().get("/console/")
    assert "검토가 필요한 것만" in response.text
    assert response.text.count("첫 검토 시작") == 1
    assert 'class="priority-queue"' in response.text
    assert "작업 01" not in response.text


def test_pending_review_rows_include_mobile_labels() -> None:
    response = _build_console_client_with_two_pending_drafts().get("/console/reviews/pending")
    assert 'data-label="채널"' in response.text
    assert 'data-label="확인 사항"' in response.text
    assert 'class="queue-row-link"' in response.text
```

- [ ] **Step 2: Run and verify failure**

```bash
pytest tests/test_console.py::test_console_home_renders_single_primary_review_action tests/test_console.py::test_pending_review_rows_include_mobile_labels -v
```

Expected: FAIL on old card/table markup.

- [ ] **Step 3: Replace the home template**

```html
{% extends "base.html" %}
{% from "console/_macros.html" import empty_state, page_intro, summary_item %}
{% block content %}
  {{ page_intro(
    "검토가 필요한 것만 남겼습니다.",
    "오래 기다린 초안부터 읽고 출처와 민감 신호를 확인한 뒤 판단합니다.",
    home_first_review_href, "첫 검토 시작"
  ) }}
  {% if home_data_error %}
    {{ empty_state("데이터 연결이 필요합니다", home_data_error, home_scheduler_href, "스케줄러 열기") }}
  {% elif home_review_rows %}
    <section class="priority-queue" aria-labelledby="priority-heading">
      <h2 id="priority-heading">먼저 볼 초안</h2>
      {% for row in home_review_rows %}
        <a class="priority-row" href="{{ row.detail_href }}">
          <span><strong>{{ row.title }}</strong><small>{{ row.account_key }}</small></span>
          <span data-label="채널">{{ row.channel }}</span>
          <span data-label="확인 사항">{{ row.review_flag }}</span>
          <span data-label="대기 시간">{{ row.wait_duration }}</span>
          <span aria-hidden="true">→</span>
        </a>
      {% endfor %}
    </section>
  {% else %}
    {{ empty_state("검토 대기열이 비어 있습니다", "새 초안을 만들려면 안전한 실행 흐름을 시작하세요.", home_scheduler_href, "스케줄러 열기") }}
  {% endif %}
{% endblock %}
```

Render `home_summary` as a three-column ruled strip after the queue.

- [ ] **Step 4: Convert pending review to a continuous queue**

Remove intro cards, metric cards, and the minimum-width table. Preserve title, account, channel, created time, queue position, and detail URL in `.queue-list` rows. Add visible mobile labels and a scheduler-linked empty state.

```html
<div class="queue-list">
  {% for row in pending_review_rows %}
    <a class="queue-row-link data-list-row" href="{{ row.detail_href }}">
      <span><strong>{{ row.title }}</strong><small>{{ row.account_key }}</small></span>
      <span data-label="채널">{{ row.channel }}</span>
      <span data-label="확인 사항">{{ row.variant_label }}</span>
      <span data-label="생성 시각">{{ row.created_at }}</span>
    </a>
  {% endfor %}
</div>
```

- [ ] **Step 5: Run home and queue tests**

```bash
pytest tests/test_console.py -k "console_home or pending_review" -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/api/templates/console/index.html app/api/templates/console/pending_review.html app/api/static/console.css tests/test_console.py
git commit -m "feat: build review-first console workspace"
```

---

### Task 4: Convert Monitoring Lists to the Editorial System

**Files:**
- Modify: `app/api/templates/console/dashboard.html`
- Modify: `app/api/templates/console/articles.html`
- Modify: `app/api/templates/console/publish_jobs.html`
- Modify: `app/api/static/console.css`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes unchanged `dashboard_*`, `article_*`, `publish_job_*` contexts.
- Produces `.run-summary`, `.data-list`, `.data-list-row`, `.status-strip`, and `data-label` markup.

- [ ] **Step 1: Write failing semantic-list tests**

```python
def test_dashboard_separates_failures_from_policy_skips(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    response = TestClient(create_app()).get(
        "/console/dashboard", params=_console_db_params(tmp_path)
    )
    assert 'id="technical-failures"' in response.text
    assert 'id="policy-skips"' in response.text
    assert "작업 02" not in response.text


# Add to `test_articles_page_renders_recent_article_rows`:
assert 'data-label="보강 상태"' in response.text

# Add to `test_publish_jobs_page_renders_rows_and_links`:
assert 'data-label="전달 상태"' in response.text
```

In the first test, define the local parameters explicitly:

```python
def _console_db_params(tmp_path: Path) -> dict[str, str]:
    return {"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"}
```

- [ ] **Step 2: Run and verify failure**

```bash
pytest tests/test_console.py::test_dashboard_separates_failures_from_policy_skips tests/test_console.py::test_articles_page_renders_recent_article_rows tests/test_console.py::test_publish_jobs_page_renders_rows_and_links -v
```

Expected: FAIL on missing IDs and labels.

- [ ] **Step 3: Rebuild dashboard hierarchy**

Render latest run as one `.run-summary`; put metrics in a ruled `.summary-strip`; render recent runs, technical failures, and policy skips as separate continuous lists. Add a duplicated, `aria-hidden="true"`, `data-marquee` status track only when latest-run data exists.

```html
{% if dashboard_latest_run %}
  <section class="run-summary">
    <h2>{{ dashboard_latest_run.workflow_name }}</h2>
    <strong>{{ dashboard_latest_run.status }}</strong>
    <span>{{ dashboard_latest_run.started_at }}</span>
    <span>{{ dashboard_latest_run.policy_guardrails }}</span>
  </section>
  <div class="status-strip" data-marquee aria-hidden="true">
    <span>{{ dashboard_latest_run.workflow_name }} · {{ dashboard_latest_run.status }} · {{ dashboard_latest_run.policy_guardrails }}</span>
    <span>{{ dashboard_latest_run.workflow_name }} · {{ dashboard_latest_run.status }} · {{ dashboard_latest_run.policy_guardrails }}</span>
  </div>
{% endif %}
<section id="technical-failures" class="data-list" aria-labelledby="technical-heading"></section>
<section id="policy-skips" class="data-list" aria-labelledby="policy-heading"></section>
```

- [ ] **Step 4: Rebuild article and publish lists**

Keep all current values and links. Use one primary title/source column and secondary state/time columns with a `data-label` on each. Visually emphasize open publish jobs with type weight and a left rule, not another color.

```html
<div class="data-list-row">
  <span><strong>{{ row.brief_title }}</strong><small>{{ row.source_title }}</small></span>
  <span data-label="전달 상태">{{ row.state }}</span>
  <span data-label="채널">{{ row.channel }}</span>
  <span data-label="생성 시각">{{ row.created_at }}</span>
  <a href="{{ row.detail_href }}">{{ row.publish_job_label }}</a>
</div>
```

- [ ] **Step 5: Add restrained row physics**

```css
.data-list-row { transition: background-color 180ms ease, transform 180ms ease; }
.data-list-row:is(:hover, :focus-within) {
  background: var(--sage-tint); transform: translateX(0.25rem);
}
@media (prefers-reduced-motion: reduce) {
  .data-list-row { transition: none; }
  .data-list-row:is(:hover, :focus-within) { transform: none; }
}
```

- [ ] **Step 6: Run page regressions**

```bash
pytest tests/test_console.py -k "dashboard or articles or publish_jobs_page" -q
```

Expected: PASS for empty and populated states.

- [ ] **Step 7: Commit**

```bash
git add app/api/templates/console/dashboard.html app/api/templates/console/articles.html app/api/templates/console/publish_jobs.html app/api/static/console.css tests/test_console.py
git commit -m "feat: redesign console monitoring lists"
```

---

### Task 5: Recompose Review Detail Around Content, Evidence, and Judgment

**Files:**
- Modify: `app/api/templates/console/review_detail.html`
- Modify: `app/api/static/console.css`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes unchanged `review_detail`, `review_detail_missing`, `review_action_forms`, `review_action_feedback`, and `pending_review_href` shapes.
- Produces `[data-review-story]`, `[data-review-pin]`, `[data-stack-card]`, `.review-copy`, `.review-evidence`, `.review-criteria`, `.review-judgment` for Task 7.
- Preserves input names `action`, `reviewer`, `reason`, `body`, `scheduled_for` and all POST targets.

- [ ] **Step 1: Write failing structure and form-contract tests**

```python
def test_review_detail_orders_content_evidence_and_judgment(tmp_path: Path) -> None:
    _write_minimal_project_config(tmp_path)
    session_factory = _build_session_factory(tmp_path)
    with session_scope(session_factory) as session:
        draft = _create_review_detail_draft(
            session, variant_index=0,
            created_at=datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc),
            include_provenance=True,
        )
    response = TestClient(create_app()).get(
        f"/console/reviews/{draft.id}",
        params={"database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}"},
    )
    content = response.text.index('id="review-content"')
    evidence = response.text.index('id="review-evidence"')
    judgment = response.text.index('id="review-judgment"')
    assert content < evidence < judgment
    assert 'data-review-story' in response.text
    assert 'data-review-pin' in response.text
    assert response.text.count('data-stack-card') >= 3
    assert 'name="action" value="approve"' in response.text
    assert 'name="action" value="reject"' in response.text
    assert 'name="action" value="edit"' in response.text
    assert 'name="reviewer"' in response.text
```

- [ ] **Step 2: Run and verify failure**

```bash
pytest tests/test_console.py::test_review_detail_orders_content_evidence_and_judgment -v
```

Expected: structure test FAILS; existing form-contract assertions remain a guardrail.

- [ ] **Step 3: Reorder the template into three chapters**

```html
<section id="review-content" class="review-copy">
  <h1>{{ review_detail.brief.title }}</h1>
  <p>{{ review_detail.channel }} · {{ review_detail.account_key }}</p>
  <div class="console-body-block">{{ review_detail.body }}</div>
</section>
<section id="review-evidence" class="review-story" data-review-story>
  <header class="review-story-heading" data-review-pin>판단에 필요한 근거</header>
  <div class="review-story-cards">
    <article data-stack-card><h2>출처와 원문</h2><a href="{{ review_detail.provenance.article_url }}">원문 열기</a></article>
    <article data-stack-card><h2>브리프와 핵심 요약</h2><p>{{ review_detail.brief.summary }}</p></article>
    <article data-stack-card><h2>보강 정보와 민감 신호</h2><p>{{ review_detail.sensitivity.review_note }}</p></article>
  </div>
</section>
<section id="review-judgment" class="review-judgment">
  <h2>판단 기록</h2>
  <p>{{ review_action_forms.state_hint }}</p>
</section>
```

Move audit history and sibling variants after judgment as secondary reference lists. Preserve all fallback messages and links.

- [ ] **Step 4: Add the horizontal review criteria**

Create keyboard-readable `<details>` panes for 정확성, 적합성, 안전성. Essential content must never be hover-only.

```css
@media (min-width: 901px) {
  .review-criteria { display: flex; }
  .review-criterion { flex: 1; transition: flex 500ms ease; }
  .review-criterion:is(:hover, :focus-within, [open]) { flex: 1.8; }
}
```

Add one lazy decorative image near the evidence heading using `https://picsum.photos/seed/editorial-review/640/240`, with `alt=""`, `aria-hidden="true"`, `loading="lazy"`, `referrerpolicy="no-referrer"`, explicit width/height, and grayscale. Image failure must not remove information.

- [ ] **Step 5: Restyle judgment forms without changing behavior**

Use one continuous judgment surface. Approve and edit are normal actions; reject is the only destructive variant. Keep schedule/manual-handoff states in the same location. Render `review_action_feedback` immediately before the related form and keep submitted values after errors.

```html
{% if review_action_feedback %}
  <div class="console-feedback" role="status">
    <strong>{{ review_action_feedback.title }}</strong>
    <p>{{ review_action_feedback.message }}</p>
  </div>
{% endif %}
{% if review_action_forms.show_pending_actions %}
  <form class="action-form" method="post" action="{{ review_action_forms.action_href }}">
    <input type="hidden" name="action" value="approve">
    <input name="reviewer" value="{{ review_action_forms.reviewer }}">
    <button class="console-button" type="submit">초안 승인</button>
  </form>
  <form class="action-form is-destructive" method="post" action="{{ review_action_forms.action_href }}">
    <input type="hidden" name="action" value="reject">
    <input name="reviewer" value="{{ review_action_forms.reviewer }}">
    <input name="reason" value="{{ review_action_forms.reject_reason }}">
    <button class="console-button" type="submit">초안 반려</button>
  </form>
{% endif %}
```

- [ ] **Step 6: Run all review tests**

```bash
pytest tests/test_console.py -k "review_detail or review_actions" -q
```

Expected: PASS for not-found, sensitivity, approve, reject, edit, schedule, manual upload, and validation errors.

- [ ] **Step 7: Commit**

```bash
git add app/api/templates/console/review_detail.html app/api/static/console.css tests/test_console.py
git commit -m "feat: focus console review detail on judgment"
```

---

### Task 6: Redesign Publish Detail and Scheduler Actions

**Files:**
- Modify: `app/api/templates/console/publish_job_detail.html`
- Modify: `app/api/templates/console/scheduler.html`
- Modify: `app/api/static/console.css`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes unchanged publish detail/action-form and scheduler contexts.
- Preserves publish names `action`, `operator`, `external_post_id`, `error_message`.
- Preserves scheduler names `action`, `live` and every existing action value.
- Produces `.publish-timeline`, `.handoff-workspace`, `.scheduler-actions`, `.scheduler-action`, `.live-confirmation`.

- [ ] **Step 1: Write failing action-locality and safety tests**

```python
def test_scheduler_keeps_live_confirmation_inside_publish_due_action() -> None:
    response = TestClient(create_app()).get("/console/scheduler")
    assert 'class="scheduler-action publish-due-action"' in response.text
    assert 'class="live-confirmation"' in response.text
    assert 'name="live"' in response.text
    assert 'name="live" checked' not in response.text
    assert "작업 07" not in response.text


# Add after the POST response in
# `test_publish_jobs_detail_action_complete_records_manual_publish_outcome`:
assert 'class="publish-timeline"' in response.text
assert 'name="action" value="complete"' not in response.text
assert 'name="action" value="fail"' not in response.text
assert 'name="action" value="cancel"' not in response.text
```

- [ ] **Step 2: Run and verify failure**

```bash
pytest tests/test_console.py::test_scheduler_keeps_live_confirmation_inside_publish_due_action tests/test_console.py::test_publish_jobs_detail_action_complete_records_manual_publish_outcome -v
```

Expected: FAIL on new hooks; existing hidden-form behavior remains green.

- [ ] **Step 3: Recompose publish detail**

Order job summary, linked draft, delivery timeline, open manual-handoff action, then source/brief reference. Render logs as a vertical ruled `.publish-timeline`. Preserve missing-job, terminal-job, success, and validation-error branches.

```html
<section class="publish-summary"><h1>{{ publish_job_detail.job_label }}</h1></section>
<section class="linked-draft"><a href="{{ publish_job_detail.review_detail_href }}">{{ publish_job_detail.draft.draft_label }}</a></section>
<ol class="publish-timeline">
  {% for log in publish_job_detail.publish_logs %}
    <li><strong>{{ log.event_type }}</strong><span>{{ log.created_at }}</span><p>{{ log.message }}</p></li>
  {% endfor %}
</ol>
{% if publish_job_action_forms.show_manual_publish_actions %}
  <section class="handoff-workspace">{{ publish_job_action_forms.action_title }}</section>
{% endif %}
```

- [ ] **Step 4: Recompose scheduler actions**

Render run-local first, followed by discover, ingest, enrich, backfill, and publish-due as full-width ruled `.scheduler-action` sections. Keep each action result directly below its originating form. Move the live checkbox into `.live-confirmation` inside publish-due and leave it unchecked.

```html
<section class="scheduler-actions">
  <form class="scheduler-action" method="post" action="{{ scheduler_action_href }}">
    <input type="hidden" name="action" value="run_local">
    <h2>뉴스 수집</h2><button type="submit">초안 생성까지 실행</button>
  </form>
  <form class="scheduler-action publish-due-action" method="post" action="{{ scheduler_action_href }}">
    <input type="hidden" name="action" value="publish_due">
    <h2>발행 예정 처리</h2>
    <label class="live-confirmation"><input name="live" type="checkbox">이번 요청만 실발행</label>
    <button type="submit">도래 작업 처리</button>
  </form>
</section>
```

- [ ] **Step 5: Run publish and scheduler tests**

```bash
pytest tests/test_console.py -k "publish_job or scheduler" -q
```

Expected: PASS for dry-run, explicit live selection, manual outcomes, and result rendering.

- [ ] **Step 6: Commit**

```bash
git add app/api/templates/console/publish_job_detail.html app/api/templates/console/scheduler.html app/api/static/console.css tests/test_console.py
git commit -m "feat: redesign console action workspaces"
```

---

### Task 7: Add Progressive GSAP Motion and Reduced-Motion Fallbacks

**Files:**
- Create: `app/api/static/console.js`
- Modify: `app/api/templates/base.html`
- Modify: `app/api/static/console.css`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes `[data-review-story]`, `[data-review-pin]`, `[data-stack-card]`, `[data-marquee]`.
- Produces desktop-only ScrollTrigger pinning/card stacking and an optional status marquee.
- Loads pinned GSAP `3.13.0` core and ScrollTrigger UMD before `console.js`.

- [ ] **Step 1: Write failing asset and load-order tests**

```python
def test_console_motion_asset_is_served_and_defensive() -> None:
    response = TestClient(create_app()).get("/console/static/console.js")
    assert response.status_code == 200
    assert "prefers-reduced-motion: reduce" in response.text
    assert "window.gsap" in response.text
    assert "window.ScrollTrigger" in response.text
    assert "data-review-story" in response.text


def test_console_shell_loads_gsap_before_local_motion() -> None:
    response = _build_empty_console_client().get("/console/")
    core = response.text.index("gsap@3.13.0/dist/gsap.min.js")
    trigger = response.text.index("gsap@3.13.0/dist/ScrollTrigger.min.js")
    local = response.text.index("/console/static/console.js")
    assert core < trigger < local
```

- [ ] **Step 2: Run and verify missing asset failure**

```bash
pytest tests/test_console.py::test_console_motion_asset_is_served_and_defensive tests/test_console.py::test_console_shell_loads_gsap_before_local_motion -v
```

Expected: FAIL because `console.js` and script tags do not exist.

- [ ] **Step 3: Add ordered deferred scripts**

```html
<script defer src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/ScrollTrigger.min.js"></script>
<script defer src="{{ console_asset_js_url }}"></script>
```

The page must remain fully functional when either CDN script fails.

- [ ] **Step 4: Implement defensive pinning and stacking**

```javascript
(() => {
  "use strict";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduceMotion.matches || !window.gsap || !window.ScrollTrigger) return;

  window.gsap.registerPlugin(window.ScrollTrigger);
  const media = window.gsap.matchMedia();
  media.add("(min-width: 901px) and (prefers-reduced-motion: no-preference)", () => {
    document.querySelectorAll("[data-review-story]").forEach((story) => {
      const heading = story.querySelector("[data-review-pin]");
      const cards = Array.from(story.querySelectorAll("[data-stack-card]"));
      if (!heading || cards.length === 0) return;
      window.ScrollTrigger.create({
        trigger: story, endTrigger: cards[cards.length - 1],
        start: "top 5rem", end: "bottom 60%", pin: heading, pinSpacing: false,
      });
      cards.forEach((card, index) => window.gsap.fromTo(
        card, { y: 72, scale: 0.96 },
        { y: 0, scale: 1, ease: "none", zIndex: index + 1,
          scrollTrigger: { trigger: card, start: "top 88%", end: "top 42%", scrub: 0.6 } },
      ));
    });
  });
})();
```

Add a separate slow linear tween for `[data-marquee]`; its duplicate content must be `aria-hidden`.

- [ ] **Step 5: Add no-JS and reduced-motion CSS guarantees**

Keep cards in normal document order by default. Only add sticky offsets in the desktop/no-preference media query. Under reduced motion, force `transform: none !important`, `animation: none !important`, and `position: static` on motion hooks.

```css
[data-stack-card] { position: relative; }
@media (min-width: 901px) and (prefers-reduced-motion: no-preference) {
  [data-stack-card] { position: sticky; top: 7rem; }
}
@media (prefers-reduced-motion: reduce) {
  [data-review-pin], [data-stack-card], [data-marquee] {
    position: static !important;
    transform: none !important;
    animation: none !important;
  }
}
```

- [ ] **Step 6: Run motion and review regressions**

```bash
pytest tests/test_console.py -k "motion or review_detail or static_asset" -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/api/static/console.js app/api/static/console.css app/api/templates/base.html tests/test_console.py
git commit -m "feat: add progressive console motion"
```

---

### Task 8: Complete Documentation, Regression, and Visual QA

**Files:**
- Modify: `README.md:43-55`
- Modify: `tests/test_console.py`
- Verify: all files changed by Tasks 1-7

**Interfaces:**
- Consumes the completed console and deterministic demo database.
- Produces final regression evidence and operator-facing entry-point copy.

- [ ] **Step 1: Add final banned-label/query regression**

```python
def test_primary_pages_remove_numbered_labels_and_keep_context(tmp_path: Path) -> None:
    _build_session_factory(tmp_path)
    client = TestClient(create_app())
    params = {
        "config_dir": "/tmp/operator-config",
        "database_url": f"sqlite+pysqlite:///{tmp_path / 'console.db'}",
    }
    for path in (
        "/console/", "/console/dashboard", "/console/articles",
        "/console/reviews/pending", "/console/publish-jobs", "/console/scheduler",
    ):
        response = client.get(path, params=params)
        assert response.status_code == 200
        assert not re.search(r"작업\s+0?[1-9]", response.text)
        assert "config_dir=%2Ftmp%2Foperator-config" in response.text
        assert "database_url=" in response.text
```

- [ ] **Step 2: Run the complete automated quality suite**

```bash
pytest -q
ruff check app tests
python -m compileall -q app
scripts/scan_secrets.sh
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 3: Update README**

Add below the console URL:

```markdown
- 첫 화면은 오래 기다린 초안과 추가 확인이 필요한 항목을 우선하는 검토 홈입니다.
- 승인, 수정, 반려, 예약, 발행 기록, 스케줄러 작업은 기존 서버 검증과 드라이런 기본값을 그대로 사용합니다.
```

- [ ] **Step 4: Build demo data and start the console**

```bash
python scripts/create_demo_db.py --output /tmp/sns-console-redesign-demo.db --force
uvicorn app.api:create_app --factory --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/console/?config_dir=config&database_url=sqlite+pysqlite:////tmp/sns-console-redesign-demo.db
```

- [ ] **Step 5: Verify 375px, 768px, and 1440px manually**

At each width verify: no horizontal scrollbar; H1 is two desktop lines and at most three mobile lines; queue is first after hero; only approved colors are visible; mobile nav keeps query strings; long titles/URLs wrap; keyboard focus is visible; reduced motion stops all motion; disabling JavaScript leaves links/forms working.

- [ ] **Step 6: Smoke primary routes**

```bash
for path in /console/ /console/dashboard /console/articles /console/reviews/pending /console/publish-jobs /console/scheduler; do
  curl --fail --silent --show-error \
    "http://127.0.0.1:8000${path}?config_dir=config&database_url=sqlite+pysqlite:////tmp/sns-console-redesign-demo.db" \
    >/dev/null
done
```

Expected: every request returns 2xx.

- [ ] **Step 7: Commit documentation and final test adjustments**

```bash
git add README.md tests/test_console.py
git commit -m "docs: describe review-first operator console"
```

- [ ] **Step 8: Review final branch state**

```bash
git status --short
git log --oneline --decorate -9
```

Expected: only the pre-existing `.superpowers/` and `README 2.md` may remain untracked; all implementation files are committed.

## Implementation References

- GSAP framework-agnostic/script-tag installation: <https://gsap.com/docs/v3/Installation/>
- ScrollTrigger pinning, scrubbing, and responsive match media: <https://gsap.com/docs/v3/Plugins/ScrollTrigger/>
- Reduced-motion CSS behavior: <https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion>
