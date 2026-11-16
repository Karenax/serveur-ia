import { useEffect, useState, useSyncExternalStore } from 'react';
import { getActivitySnapshot, subscribeActivity } from '../lib/asyncActivity';
import './async-activity.css';

/** Remains non-blocking and mounted once, across every Kiara screen. */
export function AsyncActivityIndicator() {
  const activity = useSyncExternalStore(subscribeActivity, getActivitySnapshot, () => null);
  const [visible,setVisible]=useState(false);
  const active=!!activity;
  useEffect(()=>{
    setVisible(false);
    if(!active)return;
    const timer=window.setTimeout(()=>setVisible(true),2000);
    return()=>window.clearTimeout(timer);
  },[active]);
  return <div className="async-activity-live" role="status" aria-live="polite" aria-atomic="true">
    {activity && visible && <div className="async-activity-indicator">
      <span className="async-activity-spinner" aria-hidden="true" />
      <span><strong>{activity.label}</strong>{activity.labels.length > 1 && <small>Plusieurs opérations en cours</small>}</span>
      <span className="async-activity-track" aria-hidden="true"><span /></span>
    </div>}
  </div>;
}
