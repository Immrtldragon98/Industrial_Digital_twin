import {useEffect,useState} from 'react';
import {Dashboard} from './features/dashboard/Dashboard';
import {getMe,hasToken,login,setToken} from './services/api';
import type {User} from './types/domain';
import './styles.css';
import './ai.css';

export default function App(){
  const [user,setUser]=useState<User|null>(null);
  const [checking,setChecking]=useState(hasToken());
  useEffect(()=>{
    if(!hasToken()){setChecking(false);return}
    getMe().then(setUser).catch(()=>setToken(null)).finally(()=>setChecking(false));
  },[]);
  if(checking)return <div className="auth-screen"><div className="auth-card"><div className="brand-mark">RT</div><h1>Reliability Twin</h1><p>Restoring your secure session…</p></div></div>;
  if(!user)return <Login onLogin={setUser}/>;
  return <Dashboard user={user} onLogout={()=>{setToken(null);setUser(null)}}/>;
}

function Login({onLogin}:{onLogin:(user:User)=>void}){
  const [username,setUsername]=useState('');
  const [password,setPassword]=useState('');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  async function submit(event:React.FormEvent){
    event.preventDefault(); setBusy(true); setError('');
    try{
      const result=await login(username,password);
      setToken(result.access_token); onLogin(result.user);
    }catch(error:any){setError(error?.response?.data?.detail||'Unable to sign in')}
    finally{setBusy(false)}
  }
  return <div className="auth-screen"><section className="auth-visual"><div className="brand-mark large">RT</div><div><span>WRM RELIABILITY PLATFORM</span><h1>Understand every asset.<br/>Extend equipment life.</h1><p>Current condition, complete maintenance history and evidence-grounded engineering guidance in one secure twin.</p></div><div className="auth-features"><span>Live parameters</span><span>History cards</span><span>Reliability intelligence</span></div></section><form className="auth-card" onSubmit={submit}><span className="eyebrow">SECURE ACCESS</span><h2>Sign in to Reliability Twin</h2><p>Use your Viewer, Engineer or Admin account.</p><label>Username<input autoFocus value={username} onChange={event=>setUsername(event.target.value)} required/></label><label>Password<input type="password" value={password} onChange={event=>setPassword(event.target.value)} required/></label>{error&&<div className="auth-error">{error}</div>}<button disabled={busy}>{busy?'Signing in…':'Sign in'}</button><small>Accounts are created only by the system administrator.</small></form></div>;
}
