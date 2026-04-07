"""Initial schema - all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # raw_events
    op.create_table(
        'raw_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_event_id', sa.String(200), nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(), nullable=False),
        sa.Column('fetched_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('normalized', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_type', 'source_event_id', name='uq_raw_events_source'),
    )
    op.create_index('idx_raw_events_pending', 'raw_events', ['normalized', 'fetched_at'],
                    postgresql_where=sa.text('normalized = FALSE'))

    # events
    op.create_table(
        'events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_event_id', sa.String(200)),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('content', sa.Text()),
        sa.Column('event_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('region_code', sa.String(50)),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('primary_dimension', sa.String(20), nullable=False),
        sa.Column('risk_or_relief', sa.String(10), nullable=False),
        sa.Column('severity', sa.Numeric(4, 3), nullable=False),
        sa.Column('source_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('source_confidence', sa.Numeric(4, 3), nullable=False, server_default='0.5'),
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ai_analyzed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scoring_version', sa.String(20), server_default='v1'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
        sa.CheckConstraint(
            "primary_dimension IN ('military','political','economic','social','cyber')",
            name='ck_events_primary_dimension'),
        sa.CheckConstraint("risk_or_relief IN ('risk','relief','neutral')",
                           name='ck_events_risk_or_relief'),
        sa.CheckConstraint('severity BETWEEN 0 AND 1', name='ck_events_severity'),
        sa.CheckConstraint('source_confidence BETWEEN 0 AND 1',
                           name='ck_events_source_confidence'),
    )
    op.create_index('idx_events_event_time', 'events', [sa.text('event_time DESC')])
    op.create_index('idx_events_region', 'events', ['region_code'])
    op.create_index('idx_events_type', 'events', ['event_type'])
    op.create_index('idx_events_risk_relief', 'events', ['risk_or_relief'])
    op.create_index('idx_events_ai_pending', 'events', ['ai_analyzed', 'event_time'],
                    postgresql_where=sa.text('ai_analyzed = FALSE'))

    # event_countries
    op.create_table(
        'event_countries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('country_code', sa.String(3), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_id', 'country_code', name='uq_event_countries'),
        sa.CheckConstraint("role IN ('initiator','target','affected')", name='ck_ec_role'),
    )
    op.create_index('idx_event_countries_event', 'event_countries', ['event_id'])
    op.create_index('idx_event_countries_country', 'event_countries', ['country_code'])

    # event_dimensions
    op.create_table(
        'event_dimensions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('military_score', sa.Numeric(5, 4), nullable=False, server_default='0'),
        sa.Column('political_score', sa.Numeric(5, 4), nullable=False, server_default='0'),
        sa.Column('economic_score', sa.Numeric(5, 4), nullable=False, server_default='0'),
        sa.Column('social_score', sa.Numeric(5, 4), nullable=False, server_default='0'),
        sa.Column('cyber_score', sa.Numeric(5, 4), nullable=False, server_default='0'),
        sa.Column('source', sa.String(20), nullable=False, server_default='rule'),
        sa.Column('computed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_id'),
        sa.CheckConstraint("source IN ('rule')", name='ck_ed_source'),
    )

    # event_ai_analysis
    op.create_table(
        'event_ai_analysis',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('summary_zh', sa.Text()),
        sa.Column('summary_en', sa.Text()),
        sa.Column('impact_direction', sa.String(10)),
        sa.Column('dimensions', postgresql.JSONB()),
        sa.Column('confidence', sa.Numeric(4, 3)),
        sa.Column('explanation', sa.Text()),
        sa.Column('related_tags', postgresql.ARRAY(sa.Text())),
        sa.Column('model_version', sa.String(50)),
        sa.Column('prompt_version', sa.String(20)),
        sa.Column('raw_response', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_id'),
        sa.CheckConstraint("impact_direction IN ('risk','relief','neutral')",
                           name='ck_eaia_impact'),
    )

    # event_scores
    op.create_table(
        'event_scores',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('scoring_version', sa.String(20), nullable=False),
        sa.Column('base_severity', sa.Numeric(5, 4)),
        sa.Column('scope_weight', sa.Numeric(5, 4)),
        sa.Column('geo_sensitivity', sa.Numeric(5, 4)),
        sa.Column('actor_importance', sa.Numeric(5, 4)),
        sa.Column('source_confidence', sa.Numeric(5, 4)),
        sa.Column('time_decay', sa.Numeric(5, 4)),
        sa.Column('raw_score', sa.Numeric(10, 6), nullable=False),
        sa.Column('final_score', sa.Numeric(6, 2), nullable=False),
        sa.Column('computed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_id', 'scoring_version', name='uq_event_scores_version'),
    )
    op.create_index('idx_event_scores_event', 'event_scores', ['event_id'])
    op.create_index('idx_event_scores_version', 'event_scores',
                    ['scoring_version', sa.text('computed_at DESC')])

    # country_tension_daily
    op.create_table(
        'country_tension_daily',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('country_code', sa.String(3), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('risk_score', sa.Numeric(8, 2), nullable=False, server_default='0'),
        sa.Column('relief_score', sa.Numeric(8, 2), nullable=False, server_default='0'),
        sa.Column('net_tension', sa.Numeric(5, 2), nullable=False),
        sa.Column('military_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('political_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('economic_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('social_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('cyber_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('event_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scoring_version', sa.String(20), nullable=False, server_default='v1'),
        sa.Column('computed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('country_code', 'date', 'scoring_version', name='uq_ctd'),
        sa.CheckConstraint('net_tension BETWEEN 0 AND 100', name='ck_ctd_net_tension'),
    )
    op.create_index('idx_ctd_date', 'country_tension_daily', [sa.text('date DESC')])
    op.create_index('idx_ctd_country_date', 'country_tension_daily',
                    ['country_code', sa.text('date DESC')])
    op.create_index('idx_ctd_net_tension', 'country_tension_daily',
                    [sa.text('date DESC'), sa.text('net_tension DESC')])

    # region_tension_daily
    op.create_table(
        'region_tension_daily',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('region_code', sa.String(50), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('risk_score', sa.Numeric(8, 2), nullable=False, server_default='0'),
        sa.Column('relief_score', sa.Numeric(8, 2), nullable=False, server_default='0'),
        sa.Column('net_tension', sa.Numeric(5, 2), nullable=False),
        sa.Column('military_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('political_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('economic_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('social_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('cyber_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('top_country_codes', postgresql.ARRAY(sa.Text()), nullable=False,
                  server_default='{}'),
        sa.Column('event_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scoring_version', sa.String(20), nullable=False, server_default='v1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('region_code', 'date', 'scoring_version', name='uq_rtd'),
        sa.CheckConstraint('net_tension BETWEEN 0 AND 100', name='ck_rtd_net_tension'),
    )
    op.create_index('idx_rtd_date', 'region_tension_daily', [sa.text('date DESC')])
    op.create_index('idx_rtd_region_date', 'region_tension_daily',
                    ['region_code', sa.text('date DESC')])

    # global_tension_daily
    op.create_table(
        'global_tension_daily',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('risk_score', sa.Numeric(8, 2), nullable=False, server_default='0'),
        sa.Column('relief_score', sa.Numeric(8, 2), nullable=False, server_default='0'),
        sa.Column('net_tension', sa.Numeric(5, 2), nullable=False),
        sa.Column('military_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('political_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('economic_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('social_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('cyber_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('top_risk_event_ids', postgresql.ARRAY(sa.BigInteger()), nullable=False,
                  server_default='{}'),
        sa.Column('top_relief_event_ids', postgresql.ARRAY(sa.BigInteger()), nullable=False,
                  server_default='{}'),
        sa.Column('ai_summary', sa.Text()),
        sa.Column('scoring_version', sa.String(20), nullable=False, server_default='v1'),
        sa.Column('computed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', 'scoring_version', name='uq_gtd'),
        sa.CheckConstraint('net_tension BETWEEN 0 AND 100', name='ck_gtd_net_tension'),
    )
    op.create_index('idx_gtd_date', 'global_tension_daily', [sa.text('date DESC')])

    # news_sources
    op.create_table(
        'news_sources',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('source_name', sa.String(200)),
        sa.Column('source_url', sa.Text()),
        sa.Column('title', sa.Text()),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('language', sa.String(2)),
        sa.Column('credibility_score', sa.Numeric(4, 3), server_default='0.5'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_news_sources_event', 'news_sources', ['event_id'])

    # ingest_errors
    op.create_table(
        'ingest_errors',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('error_type', sa.String(100), nullable=False),
        sa.Column('error_detail', sa.Text()),
        sa.Column('raw_data', postgresql.JSONB()),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_retry_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('occurred_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ingest_errors_unresolved', 'ingest_errors', ['occurred_at'],
                    postgresql_where=sa.text('resolved = FALSE'))


def downgrade() -> None:
    op.drop_table('ingest_errors')
    op.drop_table('news_sources')
    op.drop_table('global_tension_daily')
    op.drop_table('region_tension_daily')
    op.drop_table('country_tension_daily')
    op.drop_table('event_scores')
    op.drop_table('event_ai_analysis')
    op.drop_table('event_dimensions')
    op.drop_table('event_countries')
    op.drop_table('events')
    op.drop_table('raw_events')
