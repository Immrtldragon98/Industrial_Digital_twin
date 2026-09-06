"""component change history"""
revision='0002'; down_revision='0001'
def upgrade():
 from alembic import op
 op.execute("""CREATE TABLE IF NOT EXISTS component_changes (id UUID PRIMARY KEY, equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE, changed_at TIMESTAMPTZ NOT NULL, component_name VARCHAR(255) NOT NULL, old_component VARCHAR(255), new_component VARCHAR(255), reason TEXT, performed_by VARCHAR(255), sap_order_number VARCHAR(100), running_hours DOUBLE PRECISION, source VARCHAR(50) DEFAULT 'manual', created_at TIMESTAMPTZ DEFAULT NOW())""")
def downgrade():
 from alembic import op
 op.drop_table('component_changes')
