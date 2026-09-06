from datetime import datetime, timezone

from app.models.models import (
    ComponentChange,
    ConditionReading,
    Equipment,
    Failure,
    MaintenanceEvent,
    Parameter,
)
from app.services.reliability_service import calculate_metrics


def equipment_scope_ids(db, equipment_id):
    """Return an asset and every nested assembly/component below it."""
    equipment = db.query(Equipment.id, Equipment.parent_equipment_id).all()
    children = {}
    for item_id, parent_id in equipment:
        children.setdefault(parent_id, []).append(item_id)
    result, pending = [], [equipment_id]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        result.append(current)
        pending.extend(children.get(current, []))
    return result


def reading_status(parameter, reading):
    if not reading or reading.value is None:
        return 'NO_DATA'
    value = reading.value
    if (
        (parameter.critical_min is not None and value < parameter.critical_min)
        or (parameter.critical_max is not None and value > parameter.critical_max)
    ):
        return 'CRITICAL'
    if (
        (parameter.warning_min is not None and value < parameter.warning_min)
        or (parameter.warning_max is not None and value > parameter.warning_max)
        or (parameter.normal_min is not None and value < parameter.normal_min)
        or (parameter.normal_max is not None and value > parameter.normal_max)
    ):
        return 'WARNING'
    return 'NORMAL'


def age_hours(timestamp):
    if not timestamp:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return round(max(0, (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600), 1)


def parameter_snapshot(db, equipment_id, history_limit=30):
    scope = equipment_scope_ids(db, equipment_id)
    parameters = db.query(Parameter).filter(Parameter.equipment_id.in_(scope)).order_by(Parameter.name).all()
    equipment = {item.id: item for item in db.query(Equipment).filter(Equipment.id.in_(scope)).all()}
    result = []
    for parameter in parameters:
        readings = (
            db.query(ConditionReading)
            .filter(ConditionReading.parameter_id == parameter.id)
            .order_by(ConditionReading.timestamp.desc())
            .limit(min(max(history_limit, 1), 200))
            .all()
        )
        latest = readings[0] if readings else None
        result.append({
            'parameter_id': str(parameter.id),
            'equipment_id': str(parameter.equipment_id),
            'equipment_number': equipment[parameter.equipment_id].equipment_number,
            'equipment_name': equipment[parameter.equipment_id].name,
            'code': parameter.parameter_code,
            'name': parameter.name,
            'unit': parameter.unit,
            'limits': {
                'normal_min': parameter.normal_min,
                'normal_max': parameter.normal_max,
                'warning_min': parameter.warning_min,
                'warning_max': parameter.warning_max,
                'critical_min': parameter.critical_min,
                'critical_max': parameter.critical_max,
            },
            'status': reading_status(parameter, latest),
            'last_updated_hours_ago': age_hours(latest.timestamp) if latest else None,
            'latest': None if not latest else {
                'value': latest.value,
                'timestamp': latest.timestamp,
                'quality': latest.quality,
                'source': latest.source,
            },
            'history': [{
                'value': reading.value,
                'timestamp': reading.timestamp,
                'quality': reading.quality,
                'source': reading.source,
            } for reading in readings],
        })
    return result


def history_card(db, equipment_id):
    scope = equipment_scope_ids(db, equipment_id)
    events = []
    maintenance = db.query(MaintenanceEvent).filter(MaintenanceEvent.equipment_id.in_(scope)).all()
    failures = db.query(Failure).filter(Failure.equipment_id.in_(scope)).all()
    changes = db.query(ComponentChange).filter(ComponentChange.equipment_id.in_(scope)).all()
    equipment = {item.id: item for item in db.query(Equipment).filter(Equipment.id.in_(scope)).all()}

    for item in maintenance:
        events.append({
            'id': str(item.id), 'type': 'MAINTENANCE', 'date': item.actual_start or item.planned_start or item.created_at,
            'equipment_number': equipment[item.equipment_id].equipment_number if item.equipment_id else None,
            'title': item.title or 'Maintenance event', 'description': item.description,
            'sap_reference': item.sap_order_number, 'downtime_hours': item.downtime_hours,
        })
    for item in failures:
        events.append({
            'id': str(item.id), 'type': 'FAILURE', 'date': item.failure_start or item.created_at,
            'equipment_number': equipment[item.equipment_id].equipment_number if item.equipment_id else None,
            'title': item.failure_mode or 'Failure / breakdown', 'description': item.description,
            'cause': item.failure_cause, 'sap_reference': item.notification_number,
            'downtime_hours': item.downtime_hours,
        })
    for item in changes:
        events.append({
            'id': str(item.id), 'type': 'COMPONENT_CHANGE', 'date': item.changed_at,
            'equipment_number': equipment[item.equipment_id].equipment_number,
            'title': item.component_name, 'description': item.reason,
            'sap_reference': item.sap_order_number, 'running_hours': item.running_hours,
            'old_component': item.old_component, 'new_component': item.new_component,
        })
    def sortable_date(event):
        value = event['date']
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    events.sort(key=sortable_date, reverse=True)
    return {
        'equipment_id': str(equipment_id),
        'scope_asset_count': len(scope),
        'metrics': calculate_metrics(db, equipment_id, scope_ids=scope),
        'counts': {
            'maintenance': len(maintenance),
            'failures': len(failures),
            'component_changes': len(changes),
        },
        'timeline': events[:250],
    }
