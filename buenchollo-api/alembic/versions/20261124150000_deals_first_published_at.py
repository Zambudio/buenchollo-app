"""deals.first_published_at: la primera publicación de cada chollo.

`published_at` se renueva cuando un chollo antiguo se reactiva (comprobación de
precios, alta del mismo producto, publicación programada), así que el ranking
«Top de la semana» y el resumen de los domingos colaban chollos de hace meses.
Esta columna guarda la primera publicación y no cambia nunca.

- Relleno: la fecha más antigua conocida entre `published_at`, la primera
  publicación programada (`scheduled_deals` publicado), el primer envío a
  Telegram y, para los que no pasaron por la programación, `created_at`.
- Trigger: al pasar a `active` sin fecha, se pone `published_at` (o ahora). Así
  vale para cualquier camino (ORM o API REST de Supabase).

Revision ID: 20261124150000
Revises: 20261124130000
"""

import sqlalchemy as sa
from alembic import op

revision = "20261124150000"
down_revision = "20261124130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE public.deals d
        SET first_published_at = LEAST(
            d.published_at,
            (SELECT min(s.scheduled_at) FROM public.scheduled_deals s
              WHERE s.deal_id = d.id AND s.status = 'publicado'),
            (SELECT min(t.sent_at) FROM public.telegram_publications t WHERE t.deal_id = d.id),
            CASE WHEN NOT EXISTS (SELECT 1 FROM public.scheduled_deals s WHERE s.deal_id = d.id)
                 THEN d.created_at END
        )
        WHERE d.status <> 'scheduled'
           OR EXISTS (SELECT 1 FROM public.scheduled_deals s
                       WHERE s.deal_id = d.id AND s.status = 'publicado');
        """
    )
    op.create_index("ix_deals_status_first_published_at", "deals", ["status", "first_published_at"])
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.deals_set_first_published_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          IF NEW.status = 'active' AND NEW.first_published_at IS NULL THEN
            NEW.first_published_at := COALESCE(NEW.published_at, now());
          END IF;
          RETURN NEW;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS deals_first_published_at ON public.deals;")
    op.execute(
        """
        CREATE TRIGGER deals_first_published_at
          BEFORE INSERT OR UPDATE ON public.deals
          FOR EACH ROW EXECUTE FUNCTION public.deals_set_first_published_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS deals_first_published_at ON public.deals;")
    op.execute("DROP FUNCTION IF EXISTS public.deals_set_first_published_at();")
    op.drop_index("ix_deals_status_first_published_at", table_name="deals")
    op.drop_column("deals", "first_published_at")
