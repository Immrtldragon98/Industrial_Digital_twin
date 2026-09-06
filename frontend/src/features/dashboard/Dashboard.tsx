import {useEffect,useMemo,useState} from 'react';
import {
  askKnowledge,coachEquipment,createUser,getEquipment,getHistoryCard,getParameters,
  getSummary,getTree,getUsers,uploadData,uploadKnowledge,
} from '../../services/api';
import type {Equipment,HistoryCard,ParameterSnapshot,RagAnswer,Role,Summary,TreeNode,User} from '../../types/domain';
import {MetricCard} from '../../components/MetricCard';
import {Tree} from '../../components/Tree';

const allTabs=['Overview','Equipment twin','History card','SAP imports','Reliability intelligence','Accounts'] as const;
type Tab=(typeof allTabs)[number];
type LineFilter='ALL'|'WRM1'|'WRM2'|'WRM3';
const coachingPrompts=[
  ['Life improvement review','Review this equipment and teach me how to improve its reliability and service life.'],
  ['Repeated failure review','Identify repeated failure patterns and explain the engineering checks required.'],
  ['Parameter risk review','Review parameter trends and explain which conditions may reduce component life.'],
];

function formatAge(hours:number|null){
  if(hours===null)return 'Never updated';
  if(hours<1)return 'Less than 1 hour ago';
  if(hours<48)return `${Math.round(hours)} hours ago`;
  return `${Math.round(hours/24)} days ago`;
}
function limitsText(limits:Record<string,number|null>,unit?:string){
  const values=[
    limits.normal_min!==null||limits.normal_max!==null?`Normal ${limits.normal_min??'—'}–${limits.normal_max??'—'}`:'',
    limits.warning_min!==null||limits.warning_max!==null?`Warning ${limits.warning_min??'—'}–${limits.warning_max??'—'}`:'',
    limits.critical_min!==null||limits.critical_max!==null?`Critical ${limits.critical_min??'—'}–${limits.critical_max??'—'}`:'',
  ].filter(Boolean);
  return values.length?`${values.join(' · ')} ${unit||''}`:'Operating limits not supplied';
}
function filterTree(nodes:TreeNode[],line:LineFilter):TreeNode[]{
  if(line==='ALL')return nodes;
  return nodes.map(node=>({...node,children:filterTree(node.children,line)}))
    .filter(node=>node.type==='functional_location'?node.children.length>0:node.wrm_line===line||node.children.length>0);
}

export function Dashboard({user,onLogout}:{user:User;onLogout:()=>void}){
  const [summary,setSummary]=useState<Summary|null>(null);
  const [equipment,setEquipment]=useState<Equipment[]>([]);
  const [tree,setTree]=useState<TreeNode[]>([]);
  const [selected,setSelected]=useState('');
  const [parameters,setParameters]=useState<ParameterSnapshot[]>([]);
  const [history,setHistory]=useState<HistoryCard|null>(null);
  const [tab,setTab]=useState<Tab>('Overview');
  const [line,setLine]=useState<LineFilter>('ALL');
  const [message,setMessage]=useState('');
  const [busy,setBusy]=useState('');
  const [question,setQuestion]=useState('');
  const [rag,setRag]=useState<RagAnswer|null>(null);
  const [docType,setDocType]=useState('MANUAL');
  const [users,setUsers]=useState<User[]>([]);
  const [newUsername,setNewUsername]=useState('');
  const [newPassword,setNewPassword]=useState('');
  const [newRole,setNewRole]=useState<Role>('viewer');
  const isAdmin=user.role==='admin';
  const canWrite=user.role==='engineer'||isAdmin;
  const tabs=allTabs.filter(item=>(item!=='SAP imports'||canWrite)&&(item!=='Accounts'||isAdmin));

  async function refresh(){
    try{
      setMessage('');
      const [summaryData,equipmentData,treeData]=await Promise.all([getSummary(),getEquipment(),getTree()]);
      setSummary(summaryData); setEquipment(equipmentData); setTree(treeData);
      if(!selected&&equipmentData[0])setSelected(equipmentData[0].id);
    }catch{setMessage('API is not reachable or your session expired. Sign in again.')}
  }
  useEffect(()=>{refresh()},[]);
  useEffect(()=>{
    if(!selected){setParameters([]);setHistory(null);return}
    Promise.all([getParameters(selected),getHistoryCard(selected)])
      .then(([parameterData,historyData])=>{setParameters(parameterData);setHistory(historyData)})
      .catch(()=>{setParameters([]);setHistory(null)});
  },[selected]);
  useEffect(()=>{
    if(tab==='Accounts'&&isAdmin)getUsers().then(setUsers).catch(()=>setMessage('Unable to load accounts'));
  },[tab,isAdmin]);

  const current=useMemo(()=>equipment.find(item=>item.id===selected),[equipment,selected]);
  const visibleEquipment=useMemo(()=>line==='ALL'?equipment:equipment.filter(item=>item.wrm_line===line),[equipment,line]);
  const visibleTree=useMemo(()=>filterTree(tree,line),[tree,line]);

  function selectLine(next:LineFilter){
    setLine(next);
    if(next!=='ALL'){
      const first=equipment.find(item=>item.wrm_line===next);
      if(first)setSelected(first.id);
    }
  }
  async function upload(event:React.ChangeEvent<HTMLInputElement>,kind:string){
    const file=event.target.files?.[0]; if(!file)return;
    try{
      setBusy(kind); const result=await uploadData(file,kind);
      setMessage(`Imported ${result.rows_created} rows; updated ${result.rows_updated||0}; skipped ${result.rows_skipped}.`);
      await refresh();
      if(selected){setParameters(await getParameters(selected));setHistory(await getHistoryCard(selected))}
    }catch(error:any){setMessage(error?.response?.data?.detail||'Import failed')}
    finally{setBusy('');event.target.value=''}
  }
  async function knowledgeUpload(event:React.ChangeEvent<HTMLInputElement>){
    const file=event.target.files?.[0]; if(!file)return;
    try{
      setBusy('knowledge'); const result=await uploadKnowledge(file,docType,current?.equipment_number);
      setMessage(`Imported ${result.chunks} knowledge chunks for retrieval.`);
    }catch(error:any){setMessage(error?.response?.data?.detail||'Knowledge import failed')}
    finally{setBusy('');event.target.value=''}
  }
  async function ask(coach=false,focus?:string){
    const prompt=focus||question.trim(); if(!prompt||!selected)return;
    try{setBusy('ask');setRag(coach?await coachEquipment(selected,prompt):await askKnowledge(prompt,selected))}
    catch(error:any){setMessage(error?.response?.data?.detail||'Reliability review failed')}
    finally{setBusy('')}
  }
  async function addUser(event:React.FormEvent){
    event.preventDefault();
    try{
      setBusy('account'); await createUser(newUsername,newPassword,newRole);
      setUsers(await getUsers());
      setMessage(`Created ${newRole} account for ${newUsername.trim().toLowerCase()}.`);
      setNewUsername('');setNewPassword('');
    }catch(error:any){setMessage(error?.response?.data?.detail||'Account creation failed')}
    finally{setBusy('')}
  }

  return <div className="shell">
    <header>
      <div><div className="eyebrow">RELIABILITY INTELLIGENCE</div><h1>Reliability Twin</h1><p>Current condition · complete history · evidence-led equipment life</p></div>
      <div className="session"><span className={`role-badge ${user.role}`}>{user.role}</span><b>{user.username}</b><button onClick={onLogout}>Sign out</button></div>
    </header>
    <nav>{tabs.map(item=><button className={tab===item?'active':''} onClick={()=>setTab(item)} key={item}>{item}</button>)}</nav>
    {message&&<div className={message.startsWith('Imported')||message.startsWith('Created')?'notice':'error'}>{message}</div>}
    <section className="line-filter">
      <div><span>Production scope</span><strong>{line==='ALL'?'All Wire Rod Mills':line}</strong></div>
      {(['ALL','WRM1','WRM2','WRM3'] as LineFilter[]).map(item=><button className={line===item?'active':''} onClick={()=>selectLine(item)} key={item}><b>{item}</b><small>{item==='ALL'?equipment.length:equipment.filter(asset=>asset.wrm_line===item).length} equipment</small></button>)}
    </section>

    {tab==='Overview'&&<>
      <section className="context-strip"><span><b>FL</b> Functional location</span><span><b>EQ</b> Line equipment</span><span><b>SE</b> Sub-equipment</span><span><b>ASM</b> Assembly</span><span><b>CMP</b> Component</span></section>
      <section className="metrics"><MetricCard label="Mapped equipment" value={visibleEquipment.length}/><MetricCard label="Fleet availability" value={summary?.average_availability!==null&&summary?.average_availability!==undefined?`${summary.average_availability}%`:'Needs history'}/><MetricCard label="Reliability score" value={summary?.average_reliability??'Needs history'}/><MetricCard label="High-risk assets" value={summary?.high_risk_count??'—'}/></section>
      <main><section className="panel"><div className="panel-head"><h2>{line==='ALL'?'WRM asset hierarchy':`${line} asset hierarchy`}</h2><p>Open structure: equipment → assemblies → components</p></div>{visibleTree.length?<Tree nodes={visibleTree}/>:<div className="empty">No hierarchy is mapped for this line.</div>}</section><section className="panel"><div className="panel-head"><h2>Equipment register</h2><p>{visibleEquipment.length} assets available in this scope</p></div>{visibleEquipment.map(item=><button className="equipment-row" key={item.id} onClick={()=>{setSelected(item.id);setTab('Equipment twin')}}><span>{item.equipment_number||'—'}</span><strong>{item.name}</strong><b className="pill">{item.status}</b></button>)}{!visibleEquipment.length&&<div className="empty">No equipment mapped.</div>}</section></main>
    </>}

    {tab==='Equipment twin'&&<section className="workspace"><EquipmentList equipment={visibleEquipment} selected={selected} onSelect={setSelected}/><section className="panel twin"><EquipmentHeader equipment={current}/><div className="section-title"><h3>Current and last-updated parameters</h3><span>{parameters.length} parameters across this asset and its children</span></div><div className="parameter-table"><div className="parameter-head"><span>Parameter</span><span>Current value</span><span>Condition</span><span>Last updated</span></div>{parameters.map(item=><details className="parameter-row" key={item.parameter_id}><summary><span><b>{item.name}</b><small>{item.equipment_number} · {item.code}</small></span><strong>{item.latest?.value??'—'} {item.unit}</strong><i className={`condition ${item.status.toLowerCase()}`}>{item.status.replace('_',' ')}</i><time>{formatAge(item.last_updated_hours_ago)}</time></summary><div className="parameter-detail"><p>{limitsText(item.limits,item.unit)}</p><table><thead><tr><th>Timestamp</th><th>Value</th><th>Quality</th><th>Source</th></tr></thead><tbody>{item.history.map((reading,index)=><tr key={index}><td>{new Date(reading.timestamp).toLocaleString()}</td><td>{reading.value??'—'} {item.unit}</td><td>{reading.quality}</td><td>{reading.source||'—'}</td></tr>)}</tbody></table></div></details>)}{!parameters.length&&<div className="empty">No condition readings imported for this equipment or its assemblies.</div>}</div></section></section>}

    {tab==='History card'&&<section className="workspace"><EquipmentList equipment={visibleEquipment} selected={selected} onSelect={setSelected}/><section className="panel"><EquipmentHeader equipment={current}/>{history&&<><section className="history-summary"><MetricCard label="MTBF" value={history.metrics.mtbf_hours!==null?`${history.metrics.mtbf_hours} h`:'Needs history'}/><MetricCard label="MTTR" value={history.metrics.mttr_hours!==null?`${history.metrics.mttr_hours} h`:'Needs failures'}/><MetricCard label="Availability" value={history.metrics.availability_percent!==null?`${history.metrics.availability_percent}%`:'Needs history'}/><MetricCard label="Assets in scope" value={history.scope_asset_count}/></section><div className="history-counts"><span>{history.counts.failures} failures</span><span>{history.counts.maintenance} maintenance events</span><span>{history.counts.component_changes} component changes</span><span>{history.metrics.calculation_basis}</span></div><div className="timeline">{history.timeline.map(event=><article className={`timeline-event ${event.type.toLowerCase()}`} key={event.id}><time>{new Date(event.date).toLocaleString()}</time><div><small>{event.type.replace('_',' ')} · {event.equipment_number||'No equipment number'}</small><h3>{event.title}</h3><p>{event.description||event.cause||'Details not recorded'}</p><footer>{event.sap_reference&&<span>SAP: {event.sap_reference}</span>}{event.downtime_hours!==undefined&&<span>Downtime: {event.downtime_hours} h</span>}{event.running_hours!==undefined&&<span>Running life: {event.running_hours} h</span>}</footer></div></article>)}{!history.timeline.length&&<div className="empty">No maintenance, failure or component-change history imported.</div>}</div></>}</section></section>}

    {tab==='SAP imports'&&canWrite&&<section className="panel import-page"><div className="panel-head"><h2>Import SAP HANA exports</h2><p>{isAdmin?'Admin can import hierarchy and all history.':'Engineer can update operating data; hierarchy is controlled by Admin.'}</p></div><div className="import-grid">{[['hierarchy','Equipment hierarchy','WRM assets, assemblies and components'],['condition','Condition readings','Values, timestamps, quality and operating limits'],['maintenance','Maintenance history','Orders, work performed, dates and downtime'],['failure','Failure history','Notifications, causes, breakdowns and downtime'],['changes','Component changes','Replacement history, life, reason and SAP order']].filter(([kind])=>kind!=='hierarchy'||isAdmin).map(([kind,title,description])=><label className="import-card" key={kind}><b>{title}</b><span>{description}</span><em>{busy===kind?'Importing…':'Choose Excel file'}</em><input hidden type="file" accept=".xlsx,.xls" onChange={event=>upload(event,kind)}/></label>)}</div></section>}

    {tab==='Reliability intelligence'&&<section className="panel ai"><div className="panel-head"><h2>Engineer reliability coach</h2><p>Selected scope: {current?.equipment_number||'choose equipment'} · {current?.name||'none'}</p></div><div className="ai-tools"><div className="coach-actions">{coachingPrompts.map(([label,prompt])=><button key={label} disabled={!selected||busy==='ask'} onClick={()=>ask(true,prompt)}>{label}</button>)}</div>{canWrite&&<div className="knowledge-upload"><select value={docType} onChange={event=>setDocType(event.target.value)}><option>MANUAL</option><option>DRAWING</option><option>BOM</option><option>FMEA</option><option>RCA</option><option>HISTORY_CARD</option><option>SOP</option><option>DATASHEET</option></select><label>{busy==='knowledge'?'Indexing…':'Import equipment knowledge'}<input hidden type="file" accept=".pdf,.docx,.xlsx,.xls,.csv,.txt,.md" onChange={knowledgeUpload}/></label></div>}<div className="askbox"><textarea value={question} onChange={event=>setQuestion(event.target.value)} placeholder="Ask why a component is failing, what checks are missing, or how to extend equipment life…"/><button onClick={()=>ask(false)} disabled={!selected||busy==='ask'}>{busy==='ask'?'Reviewing evidence…':'Ask with evidence'}</button></div>{rag&&<div className="answer"><div className={`model-state ${rag.model_status}`}>AI: {rag.model_status} · Retrieval: {rag.retrieval_mode}</div><p>{rag.answer}</p><h3>Evidence used</h3>{rag.sources.map(source=><details key={source.source_id}><summary>[{source.source_id}] {source.title} · {source.document_type}</summary><p>{source.excerpt}</p></details>)}</div>}</div></section>}

    {tab==='Accounts'&&isAdmin&&<section className="accounts-layout"><form className="panel account-form" onSubmit={addUser}><div className="panel-head"><h2>Create account</h2><p>No public registration. Assign only the access required.</p></div><label>Username<input value={newUsername} onChange={event=>setNewUsername(event.target.value)} minLength={3} required/></label><label>Temporary password<input type="password" value={newPassword} onChange={event=>setNewPassword(event.target.value)} minLength={8} required/></label><label>Role<select value={newRole} onChange={event=>setNewRole(event.target.value as Role)}><option value="viewer">Viewer — read only</option><option value="engineer">Engineer — data and analysis</option><option value="admin">Admin — full control</option></select></label><button disabled={busy==='account'}>{busy==='account'?'Creating…':'Create account'}</button></form><section className="panel"><div className="panel-head"><h2>Authorized users</h2><p>{users.length} accounts</p></div>{users.map(item=><div className="user-row" key={item.id}><div className="avatar">{item.username.slice(0,2).toUpperCase()}</div><div><b>{item.username}</b><small>{item.is_active?'Active':'Disabled'}</small></div><span className={`role-badge ${item.role}`}>{item.role}</span></div>)}</section></section>}

    <footer>v0.4 · Secure WRM equipment intelligence · PostgreSQL + pgvector · Ollama/Qwen</footer>
  </div>;
}

function EquipmentList({equipment,selected,onSelect}:{equipment:Equipment[];selected:string;onSelect:(id:string)=>void}){
  return <aside className="panel equipment-list"><div className="panel-head"><h2>Equipment</h2><p>{equipment.length} in selected line</p></div>{equipment.map(item=><button className={selected===item.id?'selected':''} onClick={()=>onSelect(item.id)} key={item.id}><small>{item.equipment_number}</small>{item.name}</button>)}{!equipment.length&&<div className="empty">No equipment in this line.</div>}</aside>;
}
function EquipmentHeader({equipment}:{equipment?:Equipment}){
  return <div className="panel-head equipment-heading"><div><span className="line-tag">{equipment?.wrm_line||'WRM'}</span><h2>{equipment?.name||'Select equipment'}</h2><p>{equipment?.equipment_number||'—'} · {equipment?.criticality||'Criticality not set'}</p></div><b className="asset-status">{equipment?.status||'—'}</b></div>;
}
