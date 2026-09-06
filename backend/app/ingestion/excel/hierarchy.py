import re
from dataclasses import dataclass, field

import pandas as pd


WRM_ROOT = '3102-CH2-WRM'


def clean(value):
    return '' if pd.isna(value) else str(value).strip()


def normalized(value):
    return re.sub(r'[^a-z0-9]+', '_', clean(value).lower()).strip('_')


def is_equipment_number(value: str) -> bool:
    return bool(re.fullmatch(r'\d{6,12}', value))


@dataclass
class HierarchyRecord:
    source_id: str
    object_id: str
    name: str
    object_type: str
    parent_source_id: str = ''
    aliases: set[str] = field(default_factory=set)
    notes: str = ''


def split_object_id(source_id: str):
    """Split '(20364187)3102-CH2-WRM-WRM1' without losing either SAP identifier."""
    match = re.fullmatch(r'\((\d{6,12})\)(.+)', source_id)
    if not match:
        return source_id, {source_id}
    equipment_number, hierarchy_code = match.groups()
    return equipment_number, {source_id, equipment_number, hierarchy_code}


def parse_structured_hierarchy(file_path):
    frame = pd.read_excel(file_path, sheet_name='SAP Hierarchy', dtype=str)
    columns = {normalized(column): column for column in frame.columns}
    required = {'sap_object_type', 'object_id', 'description', 'parent_id'}
    missing = sorted(required - set(columns))
    if missing:
        raise ValueError(f"SAP Hierarchy sheet is missing columns: {', '.join(missing)}")

    records = []
    accepted_aliases = set()
    seen_source_ids = set()
    for row_number, row in frame.iterrows():
        source_id = clean(row[columns['object_id']])
        parent_id = clean(row[columns['parent_id']])
        source_type = clean(row[columns['sap_object_type']])
        if not source_id or not source_type:
            continue
        if source_id in seen_source_ids:
            raise ValueError(f'Duplicate Object ID {source_id} at Excel row {row_number + 2}')

        object_id, aliases = split_object_id(source_id)
        object_type = normalized(source_type).upper()
        name = clean(row[columns['description']]) or source_id
        notes = clean(row[columns['notes']]) if 'notes' in columns else ''

        # This pilot deliberately imports only CH2 and the WRM branch.
        is_location = object_type == 'FUNCTIONAL_LOCATION'
        accepted_location = source_id == '3102-CH2' or source_id.startswith(WRM_ROOT)
        accepted_asset = not is_location and parent_id in accepted_aliases
        if not ((is_location and accepted_location) or accepted_asset):
            continue

        record = HierarchyRecord(
            source_id=source_id,
            object_id=object_id,
            name=name,
            object_type=object_type,
            parent_source_id=parent_id,
            aliases=aliases,
            notes=notes,
        )
        records.append(record)
        accepted_aliases.update(aliases)
        seen_source_ids.add(source_id)
    return records, len(frame)


def parse_legacy_hierarchy(file_path):
    """Support the original raw SAP export made of X-prefixed rows."""
    frame = pd.read_excel(file_path, header=None)
    records = []
    current_fl_code = ''
    for _, row in frame.iterrows():
        values = [clean(value) for value in row.tolist()]
        if len(values) >= 2 and values[0].lower() == 'functional location' and values[1]:
            current_fl_code = values[1]
            records.append(HierarchyRecord(current_fl_code, current_fl_code, current_fl_code, 'FUNCTIONAL_LOCATION'))
            continue
        if len(values) < 2 or values[0].lower() != 'x' or not values[1]:
            continue
        code = values[1]
        name = values[2] if len(values) >= 3 and values[2] else code
        if is_equipment_number(code) and current_fl_code:
            records.append(HierarchyRecord(code, code, name, 'EQUIPMENT', current_fl_code, {code}))
        elif '-' in code:
            parent = '-'.join(code.split('-')[:-1])
            records.append(HierarchyRecord(code, code, name, 'FUNCTIONAL_LOCATION', parent, {code}))
            current_fl_code = code
    return records, len(frame)


def parse_hierarchy(file_path):
    workbook = pd.ExcelFile(file_path)
    if 'SAP Hierarchy' in workbook.sheet_names:
        return parse_structured_hierarchy(file_path)
    return parse_legacy_hierarchy(file_path)


def import_hierarchy(db, file_path):
    from app.models.models import Equipment, FunctionalLocation, Plant

    records, rows_read = parse_hierarchy(file_path)
    if not records:
        raise ValueError('No WRM hierarchy records were found in the workbook')

    plant = db.query(Plant).filter(Plant.code == '3102').first()
    if not plant:
        plant = Plant(code='3102', name='Plant 3102', description='Created from SAP hierarchy import')
        db.add(plant)
        db.flush()

    existing_locations = {item.code: item for item in db.query(FunctionalLocation).all()}
    existing_equipment = {
        item.equipment_number: item
        for item in db.query(Equipment).all()
        if item.equipment_number
    }
    resolved = {}
    created = updated = fl_created = fl_updated = eq_created = eq_updated = 0

    try:
        for record in records:
            if record.object_type == 'FUNCTIONAL_LOCATION':
                parent = resolved.get(record.parent_source_id)
                obj = existing_locations.get(record.object_id)
                if obj:
                    updated += 1
                    fl_updated += 1
                else:
                    obj = FunctionalLocation(code=record.object_id, source='excel')
                    db.add(obj)
                    existing_locations[record.object_id] = obj
                    created += 1
                    fl_created += 1
                obj.plant_id = plant.id
                obj.parent_id = parent.id if isinstance(parent, FunctionalLocation) else None
                obj.name = record.name
                obj.description = record.notes or None
                obj.level = max(0, record.object_id.count('-') - 1)
                db.flush()
            else:
                parent = resolved.get(record.parent_source_id)
                obj = existing_equipment.get(record.object_id)
                if obj:
                    updated += 1
                    eq_updated += 1
                else:
                    obj = Equipment(equipment_number=record.object_id, name=record.name)
                    db.add(obj)
                    existing_equipment[record.object_id] = obj
                    created += 1
                    eq_created += 1

                if isinstance(parent, FunctionalLocation):
                    functional_location = parent
                    parent_equipment = None
                elif isinstance(parent, Equipment):
                    functional_location = existing_locations.get(WRM_ROOT)
                    parent_equipment = parent
                else:
                    raise ValueError(
                        f'Parent {record.parent_source_id!r} was not resolved for {record.source_id!r}'
                    )

                obj.name = record.name
                obj.equipment_type = record.object_type
                obj.functional_location_id = functional_location.id if functional_location else None
                obj.parent_equipment_id = parent_equipment.id if parent_equipment else None
                obj.metadata_json = {
                    **(obj.metadata_json or {}),
                    'source_object_id': record.source_id,
                    'aliases': sorted(record.aliases),
                    'notes': record.notes,
                }
                db.flush()

            for alias in record.aliases:
                resolved[alias] = obj
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        'rows_read': rows_read,
        'functional_locations_found': sum(r.object_type == 'FUNCTIONAL_LOCATION' for r in records),
        'functional_locations_created': fl_created,
        'functional_locations_updated': fl_updated,
        'equipment_records_found': sum(r.object_type != 'FUNCTIONAL_LOCATION' for r in records),
        'equipment_created': eq_created,
        'equipment_updated': eq_updated,
        'rows_created': created,
        'rows_updated': updated,
        'rows_skipped': rows_read - len(records),
        'errors': [],
    }
