export interface Equipment {
  id:string; equipment_number?:string; functional_location_id?:string;
  parent_equipment_id?:string; name:string; equipment_type?:string;
  criticality?:string; status:string; wrm_line?:string;
}
export interface TreeNode {
  id:string; type:string; code?:string; name:string; level?:number;
  status?:string; wrm_line?:string; children:TreeNode[];
}
export interface Summary {
  equipment_count:number; average_availability:number|null;
  average_reliability:number|null; high_risk_count:number; metrics_ready_count?:number;
}
export interface Reading {
  value:number|null; timestamp:string; quality:string; source?:string;
}
export interface ParameterSnapshot {
  parameter_id:string; equipment_id:string; equipment_number?:string;
  equipment_name:string; code:string; name:string; unit?:string;
  status:'NORMAL'|'WARNING'|'CRITICAL'|'NO_DATA';
  last_updated_hours_ago:number|null;
  limits:Record<string,number|null>;
  latest:Reading|null; history:Reading[];
}
export interface ReliabilityMetrics {
  mtbf_hours:number|null; mttr_hours:number|null; availability_percent:number|null;
  failure_count:number; downtime_hours:number; reliability_score:number|null; risk_score:number|null;
  observation_hours?:number|null; calculation_basis?:string;
}
export interface HistoryEvent {
  id:string; type:'MAINTENANCE'|'FAILURE'|'COMPONENT_CHANGE'; date:string;
  equipment_number?:string; title:string; description?:string; cause?:string;
  sap_reference?:string; downtime_hours?:number; running_hours?:number;
  old_component?:string; new_component?:string;
}
export interface HistoryCard {
  equipment_id:string; scope_asset_count:number; metrics:ReliabilityMetrics;
  counts:{maintenance:number;failures:number;component_changes:number};
  timeline:HistoryEvent[];
}
export interface Twin {
  equipment:Equipment; parameters:unknown[]; maintenance_events:unknown[];
  failures:unknown[]; component_changes:unknown[];
}
export interface RagSource {
  source_id:string; title:string; document_type:string; excerpt:string; equipment_id?:string;
}
export interface RagAnswer {
  answer:string; sources:RagSource[]; retrieval_mode:string; model_status:string; model?:string;
}
export type Role='viewer'|'engineer'|'admin';
export interface User {id:string;username:string;role:Role;is_active:boolean}
