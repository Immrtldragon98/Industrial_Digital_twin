import axios from 'axios';
import type {Equipment,HistoryCard,ParameterSnapshot,RagAnswer,Role,Summary,TreeNode,User} from '../types/domain';

export const api=axios.create({baseURL:import.meta.env.VITE_API_URL||'http://localhost:8000/api/v1'});
const TOKEN_KEY='reliability_twin_token';
api.interceptors.request.use(config=>{
  const token=localStorage.getItem(TOKEN_KEY);
  if(token)config.headers.Authorization=`Bearer ${token}`;
  return config;
});
export function setToken(token:string|null){if(token)localStorage.setItem(TOKEN_KEY,token);else localStorage.removeItem(TOKEN_KEY)}
export function hasToken(){return Boolean(localStorage.getItem(TOKEN_KEY))}
export async function login(username:string,password:string){return (await api.post<{access_token:string;user:User}>('/auth/login',{username,password})).data}
export async function getMe(){return (await api.get<User>('/auth/me')).data}
export async function getUsers(){return (await api.get<User[]>('/auth/users')).data}
export async function createUser(username:string,password:string,role:Role){return (await api.post<User>('/auth/users',{username,password,role})).data}
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
