"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mac_address", sa.String(length=17), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("device_class", sa.String(length=64), nullable=True),
        sa.Column("manufacturer", sa.String(length=256), nullable=True),
        sa.Column("is_ble", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_classic", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("tx_power", sa.Integer(), nullable=True),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.Column("is_favorited", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("user_label", sa.String(length=256), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_devices_mac_address", "devices", ["mac_address"], unique=True)
    op.create_index("ix_devices_last_seen", "devices", ["last_seen"], unique=False)

    op.create_table(
        "sightings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("rssi", sa.Integer(), nullable=False),
        sa.Column("estimated_distance_m", sa.Float(), nullable=True),
        sa.Column("raw_advertisement", sa.Text(), nullable=True),
    )
    op.create_index("ix_sightings_device_id", "sightings", ["device_id"], unique=False)
    op.create_index("ix_sightings_timestamp", "sightings", ["timestamp"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("rule_value", sa.String(length=256), nullable=True),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_alert_events_triggered_at", "alert_events", ["triggered_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alert_events_triggered_at", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_table("alerts")
    op.drop_index("ix_sightings_timestamp", table_name="sightings")
    op.drop_index("ix_sightings_device_id", table_name="sightings")
    op.drop_table("sightings")
    op.drop_index("ix_devices_last_seen", table_name="devices")
    op.drop_index("ix_devices_mac_address", table_name="devices")
    op.drop_table("devices")
