"""standardize master merge and deactivation semantics

Revision ID: 20261027_0015
Revises: 20261023_0014
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261027_0015"
down_revision = "20261023_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "master_lifecycle_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "entity_type IN ('product','material','supplier','warehouse','company','branch','recipe')",
            name="ck_master_lifecycle_entity_type",
        ),
        sa.CheckConstraint(
            "event_type IN ('DEACTIVATED','MERGED')",
            name="ck_master_lifecycle_event_type",
        ),
        sa.CheckConstraint(
            "(event_type = 'MERGED' AND merged_into_id IS NOT NULL AND merged_into_id <> record_id) "
            "OR (event_type = 'DEACTIVATED' AND merged_into_id IS NULL)",
            name="ck_master_lifecycle_merge_target",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_master_lifecycle_record_created",
        "master_lifecycle_events",
        ["entity_type", "record_id", "created_at"],
    )

    # Enforce the active-master rule at the database boundary for every current
    # single-column FK to a governed master. Historical rows remain readable and
    # may be edited without changing their master FK; new/changed references to
    # inactive masters are rejected regardless of which API created them.
    op.execute(
        r"""
        CREATE FUNCTION public.guard_active_master_reference() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            referenced_id uuid;
            referenced_active boolean;
            company_id uuid;
            branch_id uuid;
            parent_id uuid;
            parent_active boolean;
            branch_active boolean;
            entity_label text;
        BEGIN
            IF TG_OP = 'UPDATE' AND
               (to_jsonb(NEW) -> TG_ARGV[0]) IS NOT DISTINCT FROM
               (to_jsonb(OLD) -> TG_ARGV[0]) THEN
                RETURN NEW;
            END IF;

            referenced_id := NULLIF(to_jsonb(NEW) ->> TG_ARGV[0], '')::uuid;
            IF referenced_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF TG_ARGV[1] = 'branches' THEN
                SELECT b.is_active, b.company_id INTO referenced_active, company_id
                FROM public.branches b WHERE b.id = referenced_id FOR SHARE;
                IF referenced_active IS TRUE THEN
                    SELECT c.is_active INTO parent_active
                    FROM public.companies c WHERE c.id = company_id FOR SHARE;
                    referenced_active := referenced_active AND parent_active;
                END IF;
            ELSIF TG_ARGV[1] = 'warehouses' THEN
                SELECT w.is_active, w.company_id, w.branch_id
                  INTO referenced_active, company_id, branch_id
                FROM public.warehouses w WHERE w.id = referenced_id FOR SHARE;
                IF referenced_active IS TRUE AND company_id IS NOT NULL THEN
                    SELECT c.is_active INTO parent_active
                    FROM public.companies c WHERE c.id = company_id FOR SHARE;
                    referenced_active := referenced_active AND parent_active;
                END IF;
                IF referenced_active IS TRUE AND branch_id IS NOT NULL THEN
                    SELECT b.is_active, b.company_id INTO branch_active, company_id
                    FROM public.branches b WHERE b.id = branch_id FOR SHARE;
                    referenced_active := referenced_active AND branch_active;
                    IF referenced_active IS TRUE THEN
                        SELECT c.is_active INTO parent_active
                        FROM public.companies c WHERE c.id = company_id FOR SHARE;
                        referenced_active := referenced_active AND parent_active;
                    END IF;
                END IF;
            ELSIF TG_ARGV[1] = 'recipes' THEN
                SELECT r.is_active, r.product_id INTO referenced_active, parent_id
                FROM public.recipes r WHERE r.id = referenced_id FOR SHARE;
                IF referenced_active IS TRUE THEN
                    SELECT p.is_active INTO parent_active
                    FROM public.products p WHERE p.id = parent_id FOR SHARE;
                    referenced_active := referenced_active AND parent_active;
                END IF;
            ELSE
                EXECUTE format('SELECT is_active FROM public.%I WHERE id = $1 FOR SHARE', TG_ARGV[1])
                    INTO referenced_active USING referenced_id;
            END IF;
            IF referenced_active IS FALSE THEN
                entity_label := CASE TG_ARGV[1]
                    WHEN 'products' THEN 'product'
                    WHEN 'materials' THEN 'material'
                    WHEN 'suppliers' THEN 'supplier'
                    WHEN 'warehouses' THEN 'warehouse'
                    WHEN 'companies' THEN 'company'
                    WHEN 'branches' THEN 'branch'
                    WHEN 'recipes' THEN 'recipe'
                    ELSE 'master'
                END;
                RAISE EXCEPTION 'Inactive % record cannot be selected for a new reference', entity_label
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_active_master_reference';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        r"""
        DO $$
        DECLARE
            fk record;
            trigger_name text;
        BEGIN
            FOR fk IN
                SELECT child_ns.nspname AS child_schema,
                       child.relname AS child_table,
                       child_col.attname AS child_column,
                       parent.relname AS parent_table,
                       c.oid AS constraint_oid
                FROM pg_constraint c
                JOIN pg_class child ON child.oid = c.conrelid
                JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
                JOIN pg_class parent ON parent.oid = c.confrelid
                JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
                JOIN pg_attribute child_col
                  ON child_col.attrelid = child.oid AND child_col.attnum = c.conkey[1]
                JOIN pg_attribute parent_col
                  ON parent_col.attrelid = parent.oid AND parent_col.attnum = c.confkey[1]
                WHERE c.contype = 'f'
                  AND cardinality(c.conkey) = 1
                  AND cardinality(c.confkey) = 1
                  AND parent_ns.nspname = 'public'
                  AND parent.relname IN ('products','materials','suppliers','warehouses','companies','branches','recipes')
                  AND parent_col.attname = 'id'
                  AND child_ns.nspname = 'public'
            LOOP
                trigger_name := left('trg_active_master_' || fk.constraint_oid::text, 63);
                EXECUTE format(
                    'CREATE TRIGGER %I BEFORE INSERT OR UPDATE ON %I.%I '
                    'FOR EACH ROW EXECUTE FUNCTION public.guard_active_master_reference(%L, %L)',
                    trigger_name, fk.child_schema, fk.child_table, fk.child_column, fk.parent_table
                );
            END LOOP;
        END;
        $$;
        """
    )
    op.execute(
        r"""
        CREATE FUNCTION public.prevent_merged_master_reactivation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.is_active IS FALSE AND NEW.is_active IS TRUE AND EXISTS (
                SELECT 1 FROM public.master_lifecycle_events e
                WHERE e.entity_type = TG_ARGV[0]
                  AND e.record_id = OLD.id
                  AND e.event_type = 'MERGED'
            ) THEN
                RAISE EXCEPTION 'A merged master record cannot be reactivated'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_merged_master_not_reactivated';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        r"""
        DO $$
        DECLARE
            target record;
        BEGIN
            FOR target IN
        SELECT table_name, entity_type FROM (VALUES
                    ('products','product'), ('materials','material'), ('suppliers','supplier'),
                    ('warehouses','warehouse'), ('companies','company'), ('branches','branch'),
                    ('recipes','recipe')
                ) AS masters(table_name, entity_type)
            LOOP
                EXECUTE format(
                    'CREATE TRIGGER %I BEFORE UPDATE OF is_active ON public.%I '
                    'FOR EACH ROW EXECUTE FUNCTION public.prevent_merged_master_reactivation(%L)',
                    'trg_no_reactivate_' || target.table_name, target.table_name,
                    target.entity_type
                );
            END LOOP;
        END;
        $$;
        """
    )
    op.execute(
        r"""
        CREATE FUNCTION public.prevent_master_lifecycle_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Master lifecycle history is append-only'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_master_lifecycle_append_only';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_master_lifecycle_append_only
            BEFORE UPDATE OR DELETE ON public.master_lifecycle_events
            FOR EACH ROW EXECUTE FUNCTION public.prevent_master_lifecycle_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        r"""
        DO $$
        DECLARE
            trig record;
        BEGIN
            FOR trig IN
                SELECT ns.nspname AS schema_name, tbl.relname AS table_name, t.tgname AS trigger_name
                FROM pg_trigger t
                JOIN pg_class tbl ON tbl.oid = t.tgrelid
                JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
                WHERE NOT t.tgisinternal AND (
                    t.tgname LIKE 'trg_active_master_%'
                    OR t.tgname LIKE 'trg_no_reactivate_%'
                    OR t.tgname = 'trg_master_lifecycle_append_only'
                )
            LOOP
                EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I',
                               trig.trigger_name, trig.schema_name, trig.table_name);
            END LOOP;
        END;
        $$;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS public.guard_active_master_reference()")
    op.execute("DROP FUNCTION IF EXISTS public.prevent_merged_master_reactivation()")
    op.execute("DROP FUNCTION IF EXISTS public.prevent_master_lifecycle_event_mutation()")
    op.drop_index("ix_master_lifecycle_record_created", table_name="master_lifecycle_events")
    op.drop_table("master_lifecycle_events")
