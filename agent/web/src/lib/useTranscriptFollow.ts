import {useCallback,useLayoutEffect,useRef,useState,type FocusEvent,type KeyboardEvent,type UIEvent,type WheelEvent} from 'react';

/** Follow only this scroll region. Reading or correcting an earlier passage wins. */
export function useTranscriptFollow({sessionId,live,visible,update}:{sessionId:string;live:boolean;visible:boolean;update:string}){
  const panelRef=useRef<HTMLDivElement>(null),listRef=useRef<HTMLOListElement>(null);
  const followingRef=useRef(true),lastTop=useRef(0);
  const [following,setFollowing]=useState(true);
  const markFollowing=useCallback((value:boolean)=>{followingRef.current=value;setFollowing(value);},[]);
  const scrollToLatest=useCallback((explicit=false)=>{
    const panel=panelRef.current,last=listRef.current?.lastElementChild;
    if(!live||!visible||!panel||!last||panel.clientHeight<=0)return;
    if(!explicit&&listRef.current?.querySelector('.meeting-transcript-edit')){markFollowing(false);return;}
    // Assigning this panel's scrollTop never scrolls the page, notes or focused control.
    panel.scrollTop=Math.max(0,panel.scrollTop+last.getBoundingClientRect().bottom-panel.getBoundingClientRect().bottom+12);
    lastTop.current=panel.scrollTop;
  },[live,visible,markFollowing]);
  useLayoutEffect(()=>{markFollowing(true);lastTop.current=panelRef.current?.scrollTop||0;},[sessionId,markFollowing]);
  useLayoutEffect(()=>{if(followingRef.current)scrollToLatest();},[sessionId,update,scrollToLatest]);
  const stopReading=()=>{if(live&&visible)markFollowing(false);};
  return {panelRef,listRef,following,
    returnToLive:()=>{if(!live||!visible)return;markFollowing(true);scrollToLatest(true);},
    onScroll:(event:UIEvent<HTMLDivElement>)=>{
      const panel=event.currentTarget,top=panel.scrollTop;
      if(live&&visible&&top<lastTop.current-1)markFollowing(false);
      lastTop.current=top;
    },
    onWheel:(event:WheelEvent<HTMLDivElement>)=>{if(event.deltaY<0)stopReading();},
    onKeyDown:(event:KeyboardEvent<HTMLDivElement>)=>{if(['ArrowUp','PageUp','Home'].includes(event.key))stopReading();},
    onFocusCapture:(event:FocusEvent<HTMLDivElement>)=>{if((event.target as HTMLElement).closest('.meeting-transcript-edit'))stopReading();},
  };
}
