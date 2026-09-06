from datetime import datetime

import pandas as pd

from app.models.models import (
    ComponentChange,
    ConditionReading,
    Equipment,
    Failure,
    MaintenanceEvent,
    Parameter,
)


ALIASES = {
    'equipment_number': ['equipment', 'equipment number', 'equipment no', 'eq no', 'technical object'],
    'timestamp': ['timestamp', 'reading date', 'date time', 'measuring time'],
    'value': ['value', 'measurement reading', 'reading'],
    'quality': ['quality', 'reading quality'],
    'parameter_code': ['parameter code', 'measurement point', 'measuring point', 'characteristic'],
    'parameter_name': ['parameter name', 'parameter', 'description'],
    'unit': ['unit', 'uom'],
    'normal_min': ['normal min', 'normal minimum', 'lower normal limit'],
    'normal_max': ['normal max', 'normal maximum', 'upper normal limit'],
    'warning_min': ['warning min', 'warning minimum', 'lower warning limit'],
    'warning_max': ['warning max', 'warning maximum', 'upper warning limit'],
    'critical_min': ['critical min', 'critical minimum', 'lower critical limit'],
    'critical_max': ['critical max', 'critical maximum', 'upper critical limit'],
    'order': ['order', 'order number', 'maintenance order', 'sap order'],
    'notification': ['notification', 'notification number'],
    'description': ['description', 'long text', 'short text', 'problem'],
    'start': ['start', 'actual start', 'malfunction start'],
    'end': ['end', 'actual end', 'malfunction end'],
    'downtime': ['downtime', 'breakdown duration', 'downtime hours'],
    'component': ['component', 'component name', 'part'],
    'reason': ['reason', 'cause', 'change reason'],
}


def norm(value):
    return str(value).strip().lower().replace('_', ' ') if value is not None else ''


def colmap(frame):
    result = {}
    columns = {norm(column): column for column in frame.columns}
    for key, names in ALIASES.items():
        for name in names:
            if name in columns:
                result[key] = columns[name]
                break
    return result


def value(row, mapping, key, default=None):
    result = row.get(mapping.get(key)) if mapping.get(key) is not None else default
    return default if pd.isna(result) else result


def as_float(result):
    if result is None or clean_text(result) == '':
        return None
    return float(result)


def as_datetime(result):
    if result is None or clean_text(result) == '':
        return None
    return pd.to_datetime(result).to_pydatetime()


def clean_text(result):
    return '' if result is None else str(result).strip()


def find_equipment(db, number):
    return db.query(Equipment).filter(Equipment.equipment_number == clean_text(number)).first()


def import_sap_data(db, path, kind):
    frame = pd.read_excel(path)
    mapping = colmap(frame)
    created = updated = skipped = 0
    errors = []
    if 'equipment_number' not in mapping:
        raise ValueError('Equipment Number column is required')

    for index, row in frame.iterrows():
        try:
            equipment = find_equipment(db, value(row, mapping, 'equipment_number'))
            if not equipment:
                skipped += 1
                errors.append({'row': int(index) + 2, 'error': 'Equipment not mapped'})
                continue

            was_updated = False
            if kind == 'condition':
                timestamp = as_datetime(value(row, mapping, 'timestamp'))
                reading_value = as_float(value(row, mapping, 'value'))
                if timestamp is None or reading_value is None:
                    raise ValueError('Timestamp and Value are required for condition readings')
                code = clean_text(value(row, mapping, 'parameter_code', value(row, mapping, 'parameter_name', 'PARAM')))
                parameter = db.query(Parameter).filter(
                    Parameter.equipment_id == equipment.id,
                    Parameter.parameter_code == code,
                ).first()
                if not parameter:
                    parameter = Parameter(
                        equipment_id=equipment.id,
                        parameter_code=code,
                        name=clean_text(value(row, mapping, 'parameter_name', code)),
                        source='sap_excel',
                    )
                    db.add(parameter)
                    db.flush()
                parameter.name = clean_text(value(row, mapping, 'parameter_name', parameter.name)) or parameter.name
                parameter.unit = clean_text(value(row, mapping, 'unit', parameter.unit)) or parameter.unit
                for field in ('normal_min', 'normal_max', 'warning_min', 'warning_max', 'critical_min', 'critical_max'):
                    supplied = as_float(value(row, mapping, field))
                    if supplied is not None:
                        setattr(parameter, field, supplied)
                reading = db.query(ConditionReading).filter(
                    ConditionReading.parameter_id == parameter.id,
                    ConditionReading.timestamp == timestamp,
                ).first()
                if reading:
                    reading.value = reading_value
                    reading.quality = clean_text(value(row, mapping, 'quality', reading.quality)) or 'GOOD'
                    reading.source = 'sap_excel'
                    was_updated = True
                else:
                    db.add(ConditionReading(
                        parameter_id=parameter.id,
                        timestamp=timestamp,
                        value=reading_value,
                        quality=clean_text(value(row, mapping, 'quality', 'GOOD')) or 'GOOD',
                        source='sap_excel',
                    ))

            elif kind == 'maintenance':
                order_number = clean_text(value(row, mapping, 'order'))
                item = db.query(MaintenanceEvent).filter(
                    MaintenanceEvent.equipment_id == equipment.id,
                    MaintenanceEvent.sap_order_number == order_number,
                ).first() if order_number else None
                if not item:
                    item = MaintenanceEvent(equipment_id=equipment.id, source='sap_excel')
                    db.add(item)
                else:
                    was_updated = True
                item.sap_order_number = order_number or None
                item.title = clean_text(value(row, mapping, 'description', 'Maintenance event'))
                item.description = clean_text(value(row, mapping, 'description'))
                item.actual_start = as_datetime(value(row, mapping, 'start'))
                item.actual_end = as_datetime(value(row, mapping, 'end'))
                item.downtime_hours = as_float(value(row, mapping, 'downtime')) or 0

            elif kind == 'failure':
                notification = clean_text(value(row, mapping, 'notification'))
                item = db.query(Failure).filter(
                    Failure.equipment_id == equipment.id,
                    Failure.notification_number == notification,
                ).first() if notification else None
                if not item:
                    item = Failure(equipment_id=equipment.id)
                    db.add(item)
                else:
                    was_updated = True
                item.notification_number = notification or None
                item.failure_start = as_datetime(value(row, mapping, 'start'))
                item.failure_end = as_datetime(value(row, mapping, 'end'))
                item.description = clean_text(value(row, mapping, 'description'))
                item.failure_cause = clean_text(value(row, mapping, 'reason'))
                item.downtime_hours = as_float(value(row, mapping, 'downtime')) or 0
                item.breakdown = True

            elif kind == 'changes':
                changed_at = as_datetime(value(row, mapping, 'timestamp')) or datetime.utcnow()
                component = clean_text(value(row, mapping, 'component', 'Component'))
                order_number = clean_text(value(row, mapping, 'order'))
                item = db.query(ComponentChange).filter(
                    ComponentChange.equipment_id == equipment.id,
                    ComponentChange.changed_at == changed_at,
                    ComponentChange.component_name == component,
                    ComponentChange.sap_order_number == (order_number or None),
                ).first()
                if not item:
                    item = ComponentChange(
                        equipment_id=equipment.id,
                        changed_at=changed_at,
                        component_name=component,
                        source='sap_excel',
                    )
                    db.add(item)
                else:
                    was_updated = True
                item.reason = clean_text(value(row, mapping, 'reason'))
                item.sap_order_number = order_number or None

            if was_updated:
                updated += 1
            else:
                created += 1
        except Exception as exc:
            skipped += 1
            errors.append({'row': int(index) + 2, 'error': str(exc)})
    db.commit()
    return {
        'rows_read': len(frame),
        'rows_created': created,
        'rows_updated': updated,
        'rows_skipped': skipped,
        'errors': errors,
        'detected_columns': {key: str(column) for key, column in mapping.items()},
    }
