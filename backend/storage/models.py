from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mac_address: Mapped[str] = mapped_column(String(17), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    device_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_ble: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_classic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    tx_power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(), index=True)
    is_favorited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    user_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sightings: Mapped[list[Sighting]] = relationship(back_populates="device", cascade="all, delete-orphan")
    alerts: Mapped[list[Alert]] = relationship(back_populates="device")
    alert_events: Mapped[list[AlertEvent]] = relationship(back_populates="device", cascade="all, delete-orphan")


class Sighting(Base):
    __tablename__ = "sightings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(), index=True)
    rssi: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_advertisement: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped[Device] = relationship(back_populates="sightings")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_value: Mapped[str | None] = mapped_column(String(256), nullable=True)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    device: Mapped[Device | None] = relationship(back_populates="alerts")
    events: Mapped[list[AlertEvent]] = relationship(back_populates="alert", cascade="all, delete-orphan")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(), index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    alert: Mapped[Alert] = relationship(back_populates="events")
    device: Mapped[Device] = relationship(back_populates="alert_events")
