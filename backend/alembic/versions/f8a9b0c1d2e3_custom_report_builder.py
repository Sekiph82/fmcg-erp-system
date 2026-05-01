"""custom_report_builder

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-05-01 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f8a9b0c1d2e3'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rb_report_definitions',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_code', sa.String(50), nullable=False),
        sa.Column('report_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_user_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('visibility', sa.Enum('private', 'team', 'global', name='reportvisibility'), nullable=False),
        sa.Column('data_source', sa.String(100), nullable=False),
        sa.Column('query_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('report_id'),
        sa.UniqueConstraint('report_code'),
    )

    op.create_table(
        'rb_report_fields',
        sa.Column('report_field_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_path', sa.String(200), nullable=False),
        sa.Column('alias', sa.String(200), nullable=True),
        sa.Column('data_type', sa.String(50), nullable=True),
        sa.Column('aggregation', sa.Enum('none','sum','avg','min','max','count','count_distinct', name='aggregationtype'), nullable=True),
        sa.Column('is_group_by', sa.Boolean(), nullable=True),
        sa.Column('sort_direction', sa.Enum('asc','desc', name='sortdirection'), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('visible', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('report_field_id'),
    )

    op.create_table(
        'rb_report_filters',
        sa.Column('filter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_path', sa.String(200), nullable=False),
        sa.Column('operator', sa.Enum(
            'eq','neq','gt','lt','gte','lte','between','in','like','is_null','is_not_null',
            name='filteroperator'
        ), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_to', sa.Text(), nullable=True),
        sa.Column('logical_op', sa.Enum('and','or', name='logicaloperator'), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('filter_id'),
    )

    op.create_table(
        'rb_calculated_fields',
        sa.Column('calc_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('alias', sa.String(200), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('calc_id'),
    )

    op.create_table(
        'rb_report_schedules',
        sa.Column('schedule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frequency', sa.Enum('daily','weekly','monthly','custom', name='schedulefrequency'), nullable=False),
        sa.Column('run_time', sa.String(10), nullable=True),
        sa.Column('recipients', sa.Text(), nullable=True),
        sa.Column('export_format', sa.Enum('csv','xlsx','json', name='exportformat'), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('schedule_id'),
    )

    op.create_table(
        'rb_dashboards',
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dashboard_code', sa.String(50), nullable=False),
        sa.Column('dashboard_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_user_id', sa.String(100), nullable=True),
        sa.Column('visibility', sa.Enum('private', 'team', 'global', name='reportvisibility'), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('dashboard_id'),
        sa.UniqueConstraint('dashboard_code'),
    )

    op.create_table(
        'rb_dashboard_widgets',
        sa.Column('widget_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('widget_title', sa.String(200), nullable=True),
        sa.Column('chart_type', sa.Enum('table','bar','line','pie','kpi','area','scatter', name='charttype'), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('x_axis_field', sa.String(200), nullable=True),
        sa.Column('y_axis_field', sa.String(200), nullable=True),
        sa.Column('color_field', sa.String(200), nullable=True),
        sa.Column('refresh_interval', sa.Integer(), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dashboard_id'], ['rb_dashboards.dashboard_id']),
        sa.PrimaryKeyConstraint('widget_id'),
    )

    op.create_table(
        'rb_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum(
            'builder_assistant', 'insight_generator', 'performance_optimizer',
            name='rbaiagentype'
        ), nullable=False),
        sa.Column('status', sa.Enum('pending','acknowledged','actioned','dismissed', name='rbairecstatus'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('rb_ai_recommendations')
    op.drop_table('rb_dashboard_widgets')
    op.drop_table('rb_dashboards')
    op.drop_table('rb_report_schedules')
    op.drop_table('rb_calculated_fields')
    op.drop_table('rb_report_filters')
    op.drop_table('rb_report_fields')
    op.drop_table('rb_report_definitions')
    op.execute("DROP TYPE IF EXISTS reportvisibility")
    op.execute("DROP TYPE IF EXISTS aggregationtype")
    op.execute("DROP TYPE IF EXISTS filteroperator")
    op.execute("DROP TYPE IF EXISTS logicaloperator")
    op.execute("DROP TYPE IF EXISTS sortdirection")
    op.execute("DROP TYPE IF EXISTS schedulefrequency")
    op.execute("DROP TYPE IF EXISTS exportformat")
    op.execute("DROP TYPE IF EXISTS charttype")
    op.execute("DROP TYPE IF EXISTS rbaiagentype")
    op.execute("DROP TYPE IF EXISTS rbairecstatus")
