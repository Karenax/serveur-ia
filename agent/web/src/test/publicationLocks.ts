/** Supply the browser lock API in jsdom; arbitration has dedicated tests. */
export function installPublicationLocksForTest(){
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(name:string,_options:unknown,callback:(lock:Lock)=>Promise<void>)=>
    callback({name,mode:'exclusive'} as Lock)}});
}
