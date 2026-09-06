import re
import pandas as pd
from app.models.models import Plant, FunctionalLocation, Equipment


def clean(value):
    return '' if pd.isna(value) else str(value).strip()


def is_equipment_number(value: str) -> bool:
    return bool(re.fullmatch(r'\d{6,12}', value))


def import_hierarchy(db, file_path):
    """Import the supplied SAP-style hierarchy export.

    The workbook is not a normal tabular export: functional locations and
    equipment are mixed in rows marked with `X`. Functional locations have
    hyphenated codes; numeric codes are equipment numbers. Equipment is
    attached to the most recently encountered functional location.
    """
    df = pd.read_excel(file_path, header=None)
    rows_read = len(df)
    fl_records = []
    equipment_records = []
    current_fl_code = None

    for _, row in df.iterrows():
        vals = [clean(v) for v in row.tolist()]
        if not vals:
            continue

        # Explicit header/value row such as: Functional Location | 3102-CH2
        if len(vals) >= 2 and vals[0].lower() == 'functional location' and vals[1]:
            current_fl_code = vals[1]
            fl_records.append((current_fl_code, vals[1]))
            continue

        if len(vals) < 2 or vals[0].lower() != 'x' or not vals[1]:
            continue

        code = vals[1]
        name = vals[2] if len(vals) >= 3 and vals[2] else code

        if is_equipment_number(code):
            if current_fl_code:
                equipment_records.append((code, name, current_fl_code))
            continue

        # Hyphenated codes in this export represent functional locations.
        if '-' in code:
            current_fl_code = code
            fl_records.append((code, name))

    # De-duplicate while preserving source order.
    seen = set()
    fl_records = [r for r in fl_records if not (r[0] in seen or seen.add(r[0]))]
    seen_eq = set()
    equipment_records = [r for r in equipment_records if not (r[0] in seen_eq or seen_eq.add(r[0]))]

    plant = db.query(Plant).filter(Plant.code == 'PLANT-01').first()
    if not plant:
        plant = Plant(
            code='PLANT-01',
            name='Imported Plant',
            description='Created for initial hierarchy import',
        )
        db.add(plant)
        db.flush()

    existing_fl = {x.code: x for x in db.query(FunctionalLocation).all()}
    created = updated = skipped = 0
    fl_created = fl_updated = eq_created = eq_updated = 0
    errors = []

    # Functional locations first, so equipment can reference them safely.
    for code, name in fl_records:
        try:
            obj = existing_fl.get(code)
            if obj:
                obj.name = name
                obj.plant_id = plant.id
                updated += 1
                fl_updated += 1
                continue

            parent = None
            parts = code.split('-')
            for cut in range(len(parts) - 1, 0, -1):
                candidate = '-'.join(parts[:cut])
                if candidate in existing_fl:
                    parent = existing_fl[candidate]
                    break

            obj = FunctionalLocation(
                plant_id=plant.id,
                parent_id=parent.id if parent else None,
                code=code,
                name=name,
                level=max(0, len(parts) - 1),
                source='excel',
            )
            db.add(obj)
            db.flush()
            existing_fl[code] = obj
            created += 1
            fl_created += 1
        except Exception as exc:
            db.rollback()
            errors.append({'code': code, 'error': str(exc)})
            existing_fl = {x.code: x for x in db.query(FunctionalLocation).all()}

    existing_eq = {x.equipment_number: x for x in db.query(Equipment).all() if x.equipment_number}
    for equipment_number, name, fl_code in equipment_records:
        try:
            fl = existing_fl.get(fl_code)
            if not fl:
                skipped += 1
                errors.append({
                    'equipment_number': equipment_number,
                    'error': f'Functional location not found: {fl_code}',
                })
                continue

            obj = existing_eq.get(equipment_number)
            if obj:
                obj.name = name
                obj.functional_location_id = fl.id
                updated += 1
                eq_updated += 1
                continue

            obj = Equipment(
                equipment_number=equipment_number,
                functional_location_id=fl.id,
                name=name,
            )
            db.add(obj)
            db.flush()
            existing_eq[equipment_number] = obj
            created += 1
            eq_created += 1
        except Exception as exc:
            db.rollback()
            errors.append({'equipment_number': equipment_number, 'error': str(exc)})
            existing_fl = {x.code: x for x in db.query(FunctionalLocation).all()}
            existing_eq = {x.equipment_number: x for x in db.query(Equipment).all() if x.equipment_number}

    db.commit()
    return {
        'rows_read': rows_read,
        'functional_locations_found': len(fl_records),
        'functional_locations_created': fl_created,
        'functional_locations_updated': fl_updated,
        'equipment_records_found': len(equipment_records),
        'equipment_created': eq_created,
        'equipment_updated': eq_updated,
        'rows_created': created,
        'rows_updated': updated,
        'rows_skipped': skipped,
        'errors': errors,
    }
