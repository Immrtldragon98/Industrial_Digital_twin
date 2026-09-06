import axios from 'axios';
import type {Equipment,HistoryCard,ParameterSnapshot,RagAnswer,Summary,TreeNode} from '../types/domain';

export const api=axios.create({baseURL:import.meta.env.VITE_API_URL||'http://localhost:8000/api/v1'});
export async function getSummary(){return (await api.get<Summary>('/reliability/summary')).data}
export async function getEquipment(){return (await api.get<Equipment[]>('/equipment')).data}
export async function getTree(){return (await api.get<TreeNode[]>('/equipment/tree')).data}
export async function getParameters(id:string){return (await api.get<ParameterSnapshot[]>(`/equipment/${id}/parameters`)).data}
export async function getHistoryCard(id:string){return (await api.get<HistoryCard>(`/equipment/${id}/history-card`)).data}
export async function uploadData(file:File,type:string){
  const form=new FormData(); form.append('file',file);
  return (await api.post(type==='hierarchy'?'/imports/hierarchy':`/imports/sap/${type}`,form)).data;
}
export async function uploadKnowledge(file:File,type:string,equipmentNumber?:string){
  const form=new FormData(); form.append('file',file); form.append('document_type',type);
  if(equipmentNumber) form.append('equipment_number',equipmentNumber);
  return (await api.post('/knowledge/documents',form)).data;
}
export async function askKnowledge(question:string,equipmentId?:string){
  return (await api.post<RagAnswer>('/knowledge/ask',{question,equipment_id:equipmentId||null})).data;
}
export async function coachEquipment(equipmentId:string,focus?:string){
  return (await api.post<RagAnswer>('/knowledge/coach',{equipment_id:equipmentId,focus})).data;
}
