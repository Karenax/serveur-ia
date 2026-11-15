import type { KeyboardEvent } from 'react';
export function navigateTabs(event:KeyboardEvent<HTMLElement>){
  const tabs=Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button[role="tab"]'));
  const current=tabs.indexOf(event.target as HTMLButtonElement);if(current<0)return;
  const next=event.key==='ArrowRight'?(current+1)%tabs.length:event.key==='ArrowLeft'?(current+tabs.length-1)%tabs.length:event.key==='Home'?0:event.key==='End'?tabs.length-1:null;
  if(next===null)return;event.preventDefault();tabs[next].click();tabs[next].focus();
}
