// Optional helper snippet (not required if you inline JS in Streamlit).
// Exposes: window.__HATENA_PUSH__ with methods: getStatus(), subscribe(vapid), unsubscribe()
(function(){
  async function toUint8Array(base64String){
    const b64 = base64String.replace(/-/g,'+').replace(/_/g,'/');
    const pad = '='.repeat((4 - (b64.length % 4)) % 4);
    const raw = atob(b64 + pad);
    return new Uint8Array([...raw].map(ch => ch.charCodeAt(0)));
  }
  async function ensureSw(swUrl){
    const reg = await navigator.serviceWorker.register(swUrl, {scope:'/'});
    await navigator.serviceWorker.ready;
    return reg;
  }
  async function getStatus(){
    if(!('serviceWorker' in navigator) || !('PushManager' in window)) return {supported:false};
    const reg = await navigator.serviceWorker.getRegistration('/');
    if(!reg) return {supported:true, enabled:false};
    const sub = await reg.pushManager.getSubscription();
    return {supported:true, enabled: !!sub};
  }
  async function subscribe(vapid, swUrl='/sw.js'){
    const reg = await ensureSw(swUrl);
    const key = await toUint8Array(vapid);
    const sub = await reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:key});
    return sub;
  }
  async function unsubscribe(){
    const reg = await navigator.serviceWorker.getRegistration('/');
    if(!reg) return false;
    const sub = await reg.pushManager.getSubscription();
    if(!sub) return true;
    return await sub.unsubscribe();
  }
  window.__HATENA_PUSH__ = {getStatus, subscribe, unsubscribe};
})();
