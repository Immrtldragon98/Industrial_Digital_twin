from datetime import datetime, time, timezone


def as_utc(value):
    if value is None:
        return None
    if not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def calculate_metrics(db, equipment_id, scope_ids=None):
    from app.models.models import Equipment, Failure

    scope_ids = scope_ids or [equipment_id]
    equipment = db.get(Equipment, equipment_id)
    failures = db.query(Failure).filter(Failure.equipment_id.in_(scope_ids)).all()
    downtime = sum(max(0, failure.downtime_hours or 0) for failure in failures)
    failure_dates = [as_utc(failure.failure_start) for failure in failures if failure.failure_start]
    asset_start = as_utc(equipment.commissioning_date or equipment.installation_date) if equipment else None
    candidates = [item for item in [asset_start, *failure_dates] if item]
    observation_start = min(candidates) if candidates else None
    observation_end = datetime.now(timezone.utc)
    observation_hours = max(0, (observation_end - observation_start).total_seconds() / 3600) if observation_start else None

    if observation_hours is None or observation_hours <= 0:
        mtbf = availability = reliability = risk = operating_hours = None
        basis = 'Installation/commissioning date or dated failure history is required'
    else:
        operating_hours = max(0, observation_hours - downtime)
        mtbf = operating_hours / len(failures) if failures else operating_hours
        availability = max(0, min(100, operating_hours / observation_hours * 100))
        reliability = max(0, min(100, availability - min(len(failures) * 2, 30)))
        risk = 100 - reliability
        basis = 'Calendar observation window less recorded downtime'

    return {
        'equipment_id': str(equipment_id),
        'observation_start': observation_start,
        'observation_end': observation_end,
        'observation_hours': round(observation_hours, 2) if observation_hours is not None else None,
        'operating_hours': round(operating_hours, 2) if operating_hours is not None else None,
        'mtbf_hours': round(mtbf, 2) if mtbf is not None else None,
        'mttr_hours': round(downtime / len(failures), 2) if failures else None,
        'availability_percent': round(availability, 2) if availability is not None else None,
        'failure_count': len(failures),
        'downtime_hours': round(downtime, 2),
        'reliability_score': round(reliability, 2) if reliability is not None else None,
        'risk_score': round(risk, 2) if risk is not None else None,
        'calculation_basis': basis,
    }
