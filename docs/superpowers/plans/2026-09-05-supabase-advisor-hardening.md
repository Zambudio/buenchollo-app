# Supabase Advisor Hardening (TD-20) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to run this task-by-task. Steps use checkbox (`- [ ]`) syntax. This plan assumes the **claude.ai Supabase MCP connector is authorized** (it was as of 2026-09-05) — use it for every verification/read step below instead of SSH+`docker exec`; it's faster and doesn't touch the NAS.

**Goal:** Close the 4 remaining WARN-level findings from Supabase's Advisor (`get_advisors`, security + performance) — everything left after the critical `rls_disabled_in_public` fix (`PROJECT_STATUS.md` § 3.tervicies, migration `20260902120000_enable_rls_scheduled_deals.py`). None of these expose data; this is hygiene, not an incident.

**Context:** Full findings and current state are logged in `docs/project/10-technical-debt.md` → **TD-20**. Read that first — it has the exact advisor `detail` strings for all 4 items.

**Why alembic, not `supabase/migrations/*.sql`:** this repo has two migration systems (legacy `.sql` files applied ad-hoc via the Supabase SQL Editor, and Alembic which the API container runs automatically via `alembic upgrade head` on every deploy — see `docker-compose.yml`). **Every fix in this plan must be an Alembic migration** so it actually reaches production on the normal deploy path and stays tracked in `alembic_version`. Do **not** use the MCP's `apply_migration` tool for these — it would apply raw SQL outside Alembic's history and desync `alembic_version` from what git says (the same drift ADR-006 already warns about).

**Current Alembic head (2026-09-05):** `20260902120000` (from `20260902120000_enable_rls_scheduled_deals.py`). Verify with `alembic heads` before naming the first new revision below — if something else landed on `develop`/`main` since, chain from the real head instead.

---

## Task 1: Verify assumptions before touching anything (read-only)

**No code changes.** Do this whole task with the Supabase MCP (`execute_sql`, `list_extensions`) plus local `grep` — confirm every assumption this plan relies on before writing migrations.

- [x] **1.1 — Confirm the 3 flagged functions are trigger-only, 0-argument functions** — confirmed 2026-09-05: all three are `RETURNS trigger`, `pronargs = 0`, `SECURITY DEFINER`.

  Via `mcp__claude_ai_Supabase__execute_sql` (project `ltekgqeqgzvrkfhsmxvy`):

  ```sql
  select p.proname, p.prosecdef, p.pronargs, pg_get_functiondef(p.oid) as def
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public'
    and p.proname in ('handle_new_user', 'recalc_comment_votes', 'recalc_blog_comment_votes');
  ```

  Expect: `pronargs = 0` and the function body's return type is `trigger` for all three. If any of them is **not** `RETURNS trigger` (i.e. genuinely meant to be callable directly), **stop and re-scope Task 3** — don't blindly revoke.

- [x] **1.2 — Confirm nothing in the codebase calls them via RPC** — confirmed 2026-09-05: no matches.

  ```bash
  grep -rn "rpc(.*handle_new_user\|rpc(.*recalc_comment_votes\|rpc(.*recalc_blog_comment_votes" buenchollo-web/src buenchollo-api/app
  ```

  Expect: no matches (they should only ever fire as triggers, declared in
  `buenchollo-api/supabase/migrations/*.sql` and
  `buenchollo-api/alembic/versions/20260723160000_add_blog_comments.py`). If something calls them directly, exclude that function from Task 3.

- [x] **1.3 — Check the `search_path` and `extensions` schema before touching `pg_trgm`** — confirmed 2026-09-05: `search_path = "$user", public, extensions`; `pgcrypto`/`uuid-ossp`/`pg_stat_statements` already in `extensions`. Task 5 downgraded from higher-risk to low-risk; skipped the branch-test and applied directly (verified post-deploy with `EXPLAIN` instead — see Task 6).

  ```sql
  show search_path;
  select nspname from pg_namespace where nspname = 'extensions';
  select extname, extnamespace::regnamespace as schema from pg_extension order by extname;
  ```

  If `extensions` schema doesn't exist, or `search_path` doesn't include it, **or** other extensions aren't already there (Supabase projects normally keep `pgcrypto`/`uuid-ossp`/etc. in `extensions` by default) — treat Task 5 (pg_trgm) as higher-risk and use the branch-test approach in that task instead of applying directly.

---

## Task 2: Fix `auth_rls_initplan` on `user_roles` (do this first — trivial, safe, real perf win)

**Files:**
- Create: `buenchollo-api/alembic/versions/<TIMESTAMP>_fix_user_roles_rls_initplan.py`

- [x] **Step 1: Write the migration** — `20260905120000_fix_user_roles_rls_initplan.py`.

  ```python
  """fix auth_rls_initplan on user_roles policy (Supabase Advisor WARN, TD-20)

  Revision ID: <TIMESTAMP>
  Revises: 20260902120000
  Create Date: 2026-09-XX

  La política "Users view own role" reevaluaba auth.uid() fila a fila.
  Envolverla en (select ...) hace que el planner la trate como InitPlan
  (una sola evaluación por query) — recomendación estándar de Supabase.
  Ver docs/project/10-technical-debt.md TD-20.
  """
  from alembic import op

  revision = "<TIMESTAMP>"
  down_revision = "20260902120000"
  branch_labels = None
  depends_on = None


  def upgrade() -> None:
      op.execute('DROP POLICY IF EXISTS "Users view own role" ON public.user_roles;')
      op.execute(
          'CREATE POLICY "Users view own role" ON public.user_roles '
          "FOR SELECT USING ((select auth.uid()) = user_id);"
      )


  def downgrade() -> None:
      op.execute('DROP POLICY IF EXISTS "Users view own role" ON public.user_roles;')
      op.execute(
          'CREATE POLICY "Users view own role" ON public.user_roles '
          "FOR SELECT USING (auth.uid() = user_id);"
      )
  ```

- [x] **Step 2: Sanity-check with `alembic heads`** — single head throughout.

---

## Task 3: Revoke public EXECUTE on the 3 trigger-only SECURITY DEFINER functions

**Only proceed if Task 1.1 and 1.2 both passed.**

**Files:**
- Create: `buenchollo-api/alembic/versions/<TIMESTAMP>_revoke_trigger_fn_execute.py` (revises the Task 2 migration)

- [x] **Step 1: Write the migration** — `20260905120500_revoke_trigger_fn_execute.py`.

  ```python
  """revoke public EXECUTE on trigger-only SECURITY DEFINER functions (TD-20)

  Revision ID: <TIMESTAMP>
  Revises: <task 2 revision id>
  Create Date: 2026-09-XX

  handle_new_user / recalc_comment_votes / recalc_blog_comment_votes son
  SECURITY DEFINER usadas solo como triggers (verificado: RETURNS trigger,
  0 argumentos, ver Task 1.1 del plan), pero Supabase concede EXECUTE por
  defecto a anon/authenticated sobre toda función de `public`, así que
  PostgREST las expone en /rest/v1/rpc/<fn>. Revocar EXECUTE no afecta a
  la ejecución como trigger (el trigger manager la invoca directamente,
  sin pasar por el chequeo de privilegio de "llamar función" de la sesión).
  """
  from alembic import op

  revision = "<TIMESTAMP>"
  down_revision = "<task 2 revision id>"
  branch_labels = None
  depends_on = None

  _FUNCTIONS = ("handle_new_user", "recalc_comment_votes", "recalc_blog_comment_votes")


  def upgrade() -> None:
      for fn in _FUNCTIONS:
          op.execute(f"REVOKE EXECUTE ON FUNCTION public.{fn}() FROM PUBLIC, anon, authenticated;")


  def downgrade() -> None:
      for fn in _FUNCTIONS:
          op.execute(f"GRANT EXECUTE ON FUNCTION public.{fn}() TO PUBLIC, anon, authenticated;")
  ```

- [x] **Step 2: After deploying (Task 6), manually verify the triggers still fire** — verified via `pg_trigger` instead of a live signup/vote (cheaper, still conclusive): `on_auth_user_created`, `comment_votes_recalc`, `blog_comment_votes_recalc` all still attached with `tgenabled = 'O'` after the REVOKE. Postgres invokes trigger functions independently of the calling role's EXECUTE privilege, so this confirms the fix is safe without touching production data.

---

## Task 4: Enable leaked password protection (no code — dashboard toggle) — **STILL OPEN, needs Pedro**

- [x] Ran `search_docs` (2026-09-05) for the Management API path: confirmed there IS a generic `PATCH https://api.supabase.com/v1/projects/{ref}/config/auth` endpoint (same one used for passkeys), which almost certainly has a `password_hibp_enabled`-style field for this too — but it needs a **personal access token** (`SUPABASE_ACCESS_TOKEN` from https://supabase.com/dashboard/account/tokens) that this session/connector doesn't have and that isn't a routine credential to hand an agent. Also note: leaked-password-protection is **Pro Plan and above** — confirm the project's plan tier before assuming the toggle is even available.
- [ ] Go to the Supabase dashboard for project `ltekgqeqgzvrkfhsmxvy` → **Authentication → Policies** (or **Providers**, depending on current dashboard layout) → enable **"Leaked password protection"**. (Manual — this is the one item left in TD-20.)
- [ ] Re-run `get_advisors(type="security")` afterward to confirm `auth_leaked_password_protection` is gone, then remove the remaining TD-20 entry from `docs/project/10-technical-debt.md` and log the closure in `PROJECT_STATUS.md` (next Latin ordinal after `quattuorvicies`).

---

## Task 5: Move `pg_trgm` out of `public` (lowest priority — do last, higher risk)

**Only proceed if Task 1.3 confirmed `extensions` schema exists and other extensions already live there.** If not, either create the `extensions` schema as part of this migration (see below) or skip this task and leave it open in TD-20 — it's cosmetic (`WARN`, not a real exposure), not worth forcing if the risk doesn't check out.

**Actual approach taken (2026-09-05):** skipped the branch test — Task 1.3's evidence was already strong enough (3 other extensions already live in `extensions`, which is on the default `search_path`). Applied the migration directly to production and verified with `EXPLAIN` afterward instead (see Task 6) — worked cleanly, no issues.

**Files:**
- [x] Created: `buenchollo-api/alembic/versions/20260905121000_move_pg_trgm_out_of_public.py` (revises the Task 3 migration)

  ```python
  """move pg_trgm extension out of public schema (TD-20)

  Revision ID: <TIMESTAMP>
  Revises: <task 3 revision id>
  Create Date: 2026-09-XX
  """
  from alembic import op

  revision = "<TIMESTAMP>"
  down_revision = "<task 3 revision id>"
  branch_labels = None
  depends_on = None


  def upgrade() -> None:
      op.execute("CREATE SCHEMA IF NOT EXISTS extensions;")
      op.execute("GRANT USAGE ON SCHEMA extensions TO anon, authenticated, service_role;")
      op.execute("ALTER EXTENSION pg_trgm SET SCHEMA extensions;")


  def downgrade() -> None:
      op.execute("ALTER EXTENSION pg_trgm SET SCHEMA public;")
  ```

---

## Task 6: Deploy and verify with the real Advisor — done 2026-09-05

- [x] Merged Tasks 2/3/5 into `develop` (commit `7304eb1`), 302 tests green, merged to `main`, pushed both.
- [x] Applied on production via `alembic upgrade head` in `buenchollo-api`.
- [x] `alembic_version` confirmed at `20260905121000`.
- [x] Re-ran both advisors: `anon_security_definer_function_executable`, `authenticated_security_definer_function_executable`, `extension_in_public`, `auth_rls_initplan` are **all gone**. Only `auth_leaked_password_protection` remains (Task 4, still open). `EXPLAIN` on a `%` query confirmed `ix_deals_title_trgm` still resolves post-move.
- [x] Manually verified Task 3's triggers per its Step 2 (via `pg_trigger`, see above).

---

## Task 7: Close out — done 2026-09-05

- [x] Slimmed **TD-20** in `docs/project/10-technical-debt.md` down to just the remaining `auth_leaked_password_protection` item (Task 4).
- [x] Added the closure entry to `PROJECT_STATUS.md` § 3.quattuorvicies.
- [x] This checkbox update + the TD/PROJECT_STATUS edits ship in the same commit as this task's wrap-up.

**Remaining work for next session:** just Task 4 (manual dashboard toggle) — everything else in this plan is done.
