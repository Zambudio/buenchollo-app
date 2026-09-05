# Supabase Advisor Hardening (TD-20) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to run this task-by-task. Steps use checkbox (`- [ ]`) syntax. This plan assumes the **claude.ai Supabase MCP connector is authorized** (it was as of 2026-09-05) — use it for every verification/read step below instead of SSH+`docker exec`; it's faster and doesn't touch the NAS.

**Goal:** Close the 4 remaining WARN-level findings from Supabase's Advisor (`get_advisors`, security + performance) — everything left after the critical `rls_disabled_in_public` fix (`PROJECT_STATUS.md` § 3.tervicies, migration `20260902120000_enable_rls_scheduled_deals.py`). None of these expose data; this is hygiene, not an incident.

**Context:** Full findings and current state are logged in `docs/project/10-technical-debt.md` → **TD-20**. Read that first — it has the exact advisor `detail` strings for all 4 items.

**Why alembic, not `supabase/migrations/*.sql`:** this repo has two migration systems (legacy `.sql` files applied ad-hoc via the Supabase SQL Editor, and Alembic which the API container runs automatically via `alembic upgrade head` on every deploy — see `docker-compose.yml`). **Every fix in this plan must be an Alembic migration** so it actually reaches production on the normal deploy path and stays tracked in `alembic_version`. Do **not** use the MCP's `apply_migration` tool for these — it would apply raw SQL outside Alembic's history and desync `alembic_version` from what git says (the same drift ADR-006 already warns about).

**Current Alembic head (2026-09-05):** `20260902120000` (from `20260902120000_enable_rls_scheduled_deals.py`). Verify with `alembic heads` before naming the first new revision below — if something else landed on `develop`/`main` since, chain from the real head instead.

---

## Task 1: Verify assumptions before touching anything (read-only)

**No code changes.** Do this whole task with the Supabase MCP (`execute_sql`, `list_extensions`) plus local `grep` — confirm every assumption this plan relies on before writing migrations.

- [ ] **1.1 — Confirm the 3 flagged functions are trigger-only, 0-argument functions**

  Via `mcp__claude_ai_Supabase__execute_sql` (project `ltekgqeqgzvrkfhsmxvy`):

  ```sql
  select p.proname, p.prosecdef, p.pronargs, pg_get_functiondef(p.oid) as def
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public'
    and p.proname in ('handle_new_user', 'recalc_comment_votes', 'recalc_blog_comment_votes');
  ```

  Expect: `pronargs = 0` and the function body's return type is `trigger` for all three. If any of them is **not** `RETURNS trigger` (i.e. genuinely meant to be callable directly), **stop and re-scope Task 3** — don't blindly revoke.

- [ ] **1.2 — Confirm nothing in the codebase calls them via RPC**

  ```bash
  grep -rn "rpc(.*handle_new_user\|rpc(.*recalc_comment_votes\|rpc(.*recalc_blog_comment_votes" buenchollo-web/src buenchollo-api/app
  ```

  Expect: no matches (they should only ever fire as triggers, declared in
  `buenchollo-api/supabase/migrations/*.sql` and
  `buenchollo-api/alembic/versions/20260723160000_add_blog_comments.py`). If something calls them directly, exclude that function from Task 3.

- [ ] **1.3 — Check the `search_path` and `extensions` schema before touching `pg_trgm`**

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

- [ ] **Step 1: Write the migration**

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

- [ ] **Step 2: Sanity-check with `alembic heads`** (must stay a single head, chained after `20260902120000`).

---

## Task 3: Revoke public EXECUTE on the 3 trigger-only SECURITY DEFINER functions

**Only proceed if Task 1.1 and 1.2 both passed.**

**Files:**
- Create: `buenchollo-api/alembic/versions/<TIMESTAMP>_revoke_trigger_fn_execute.py` (revises the Task 2 migration)

- [ ] **Step 1: Write the migration**

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

- [ ] **Step 2: After deploying (Task 6), manually verify the triggers still fire** — e.g. sign up a throwaway test user (or check `handle_new_user`'s effect on `profiles`), and add/remove a comment vote to confirm `recalc_comment_votes` still updates the aggregate. Don't skip this — it's the one step that actually proves the REVOKE didn't break anything.

---

## Task 4: Enable leaked password protection (no code — dashboard toggle)

- [ ] Go to the Supabase dashboard for project `ltekgqeqgzvrkfhsmxvy` → **Authentication → Policies** (or **Providers**, depending on current dashboard layout) → enable **"Leaked password protection"**.
- [ ] Before doing it manually, run `mcp__claude_ai_Supabase__search_docs` for "leaked password protection management api" — if a Management API / MCP tool exists to toggle this by 2026-09, use it instead and note that in this file for next time. As of the 2026-09-05 tool list (`get_advisors`, `execute_sql`, `list_*`, `apply_migration`, `deploy_edge_function`, ...) there was no auth-config tool, so this was expected to stay manual.
- [ ] Re-run `get_advisors(type="security")` afterward to confirm `auth_leaked_password_protection` is gone.

---

## Task 5: Move `pg_trgm` out of `public` (lowest priority — do last, higher risk)

**Only proceed if Task 1.3 confirmed `extensions` schema exists and other extensions already live there.** If not, either create the `extensions` schema as part of this migration (see below) or skip this task and leave it open in TD-20 — it's cosmetic (`WARN`, not a real exposure), not worth forcing if the risk doesn't check out.

**Recommended: test on a Supabase branch first**, since this MCP connector has branching:
- [ ] `mcp__claude_ai_Supabase__create_branch` off `ltekgqeqgzvrkfhsmxvy`.
- [ ] On the branch, run the migration SQL below directly via `execute_sql`, then `EXPLAIN` a query that uses `ix_deals_title_trgm` (e.g. `EXPLAIN SELECT * FROM deals WHERE title % 'iphone';`) to confirm the trigram operator still resolves and the index is still used.
- [ ] If it works cleanly, write the real Alembic migration below and apply it to production the normal way (Task 6). If it breaks, either add `extensions` to the DB role's `search_path` explicitly in the same migration, or abandon this task and leave `extension_in_public` as accepted risk in TD-20 with a note why.

**Files:**
- Create: `buenchollo-api/alembic/versions/<TIMESTAMP>_move_pg_trgm_out_of_public.py` (revises the Task 3 migration)

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

## Task 6: Deploy and verify with the real Advisor

- [ ] Merge whichever of Tasks 2/3/5 were completed into `develop`, run the full backend test suite (`pytest`), merge to `main`, push both (same flow as the `scheduled_deals` RLS fix — see `PROJECT_STATUS.md` § 3.tervicies for the exact commands).
- [ ] Apply on production: `ssh -o BatchMode=yes nas-zambu 'sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker exec buenchollo-api alembic upgrade head'`.
- [ ] Verify `alembic_version` advanced to the new head (same pattern as the `scheduled_deals` verification in § 3.tervicies).
- [ ] Re-run **both** `mcp__claude_ai_Supabase__get_advisors(type="security")` and `type="performance")` — confirm the specific 4 findings from TD-20 are gone. (New INFO-level noise like `unindexed_foreign_keys` / `unused_index` is expected and NOT part of this plan's scope — don't chase it here.)
- [ ] Manually verify Task 3's triggers per its Step 2.

---

## Task 7: Close out

- [ ] Delete the **TD-20** entry from `docs/project/10-technical-debt.md` (whatever sub-items got fixed; if Task 5 was skipped, keep a slimmed-down TD-20 with just the `pg_trgm` item and explain why it's parked).
- [ ] Add the closure entry to `PROJECT_STATUS.md` — next Latin-ordinal section after the last one in the file (check the top of `## 3. Historial de refactorización completada` for whatever `### 3.<ordinal>` is currently newest; keep following the file's existing sequence: …unvicies(21), duovicies(22), tervicies(23), next is quattuorvicies(24)). Summarize what got fixed, what got verified via Advisor, and what (if anything) got parked and why.
- [ ] Same commit carries the doc updates (per `.claude/memory/feedback_forma_trabajo_iterativa.md`: docs go in the same commit as the change, not a follow-up).
