package net.karenax.fred;

import android.content.Context;
import org.json.*;
import java.util.*;

/** Contract consumed by the same chat, project, corrector and task UI as the desktop app. */
final class ClientBackend implements AutoCloseable {
    private static final List<String> REASONING_EFFORTS=Arrays.asList("none","minimal","low","medium","high","xhigh","max","ultra","on");
    final Remote remote;
    final HistorySync history;
    final String key="local_"+Json.token();
    final String bootstrap=Json.token();
    final String identity;
    final NativeNotifications notifications;
    final AndroidUpdates updates;
    private final SecureStore store;
    private JSONObject settings;
    private final JSONObject guestHistory=HistorySync.empty();
    ClientBackend(Context context,SecureStore store,JSONObject profile,boolean demo)throws Exception {this.store=store;identity=demo?"demo":profile==null?"guest":Profile.identity(profile);settings=store.read(identity+".settings");if(settings==null)settings=new JSONObject();remote=new Remote(context,profile,settings,demo,store);history=new HistorySync(store,remote,identity);notifications=new NativeNotifications(context,store,identity);updates=new AndroidUpdates(context,remote,demo);}
    synchronized JSONObject state(int port)throws Exception {history.schedule();remote.refreshDiagnostic();updates.schedule(false);return Json.object("version",BuildConfig.VERSION_NAME,"logged_in",remote.hasProfile(),"username",remote.hasProfile()?Profile.name(remote.profile):"Accès personnel","profile_required",!remote.hasProfile(),"profile",remote.hasProfile()?Json.object("name",Profile.name(remote.profile)):null,"endpoint",remote.endpoint(),"internet_endpoint",remote.hasProfile()?remote.profile.getJSONObject("wireguard").getString("endpoint"):"","connection",remote.state(),"history",history.status(),"preferences",settings.optJSONObject("preferences")==null?new JSONObject():settings.optJSONObject("preferences"),"update",updates.state(),"local_api","http://127.0.0.1:"+port+"/v1","key",key);}
    JSONObject get(String path,int port)throws Exception {switch(path){case "/client/state":return state(port);case "/client/history":if(!remote.hasProfile())return Json.object("history",guestHistory,"revision","","server_synced",false,"pending",true,"message","Importez votre accès personnel.");return history.read();case "/client/draft":JSONObject draft=store.read(identity+".draft");return draft==null?Json.object("draft",null):draft;case "/client/integrations":return Json.object("apps",new JSONArray());case "/v1/models":JSONObject state=remote.check();if(!remote.available()||!remote.hasCatalogue())throw new Remote.HttpError(state.optString("code").startsWith("access_")?401:503,Json.object("error",Json.object("code",state.optString("code"),"message",state.optString("error"))));return remote.modelCatalog();default:throw new IllegalArgumentException("Route non disponible.");}}
    JSONObject post(String path,JSONObject body)throws Exception {switch(path){case "/client/endpoint":String endpoint=body.optString("endpoint",remote.hasProfile()?remote.profile.getJSONObject("wireguard").getString("endpoint"):Profile.HTTPS);selectEndpoint(endpoint);return Json.object("endpoint",remote.endpoint());case "/client/preferences":return savePreferences(body);case "/client/history":if(!remote.hasProfile())return Json.object("saved",false,"revision","","pending",true,"message","Importez votre accès personnel.");return history.write(body.optJSONObject("history"),body.optString("revision"));case "/client/history/sync":return history.synchronize(body.optJSONObject("initial"));case "/client/history/restore-ack":return history.acknowledgeRestore(body.optBoolean("confirm"));case "/client/history/flush":return history.flush();case "/client/history/recover":return history.recover(body.optJSONObject("history"));case "/client/draft":return saveDraft(body);case "/client/update/check":updates.schedule(true);return updates.state();case "/client/update/apply":throw new IllegalArgumentException("Les mises à jour Windows ne peuvent pas s’installer sur Android.");default:throw new IllegalArgumentException("Route non disponible.");}}
    synchronized void selectMode(String mode)throws Exception {if(!remote.hasProfile())throw new IllegalArgumentException("Importez votre accès personnel.");if(!Arrays.asList("https","wireguard").contains(mode))throw new IllegalArgumentException("Choisissez HTTPS ou WireGuard.");selectEndpoint(mode.equals("https")?Profile.HTTPS:remote.profile.getJSONObject("wireguard").getString("endpoint"));}
    synchronized void selectEndpoint(String endpoint)throws Exception {remote.select(endpoint);settings.put("connection_selected",true);settings.put("endpoint",remote.endpoint());store.write(identity+".settings",settings);}
    private synchronized JSONObject savePreferences(JSONObject values)throws Exception {
        Json.keys(values,"theme","font","text_size","thinking_effort","thinking_by_model","thinking","sidebar_collapsed","corrector_text");
        Map<String,List<String>> allowed=new HashMap<>();allowed.put("theme",Arrays.asList("light","dark","system"));allowed.put("font",Arrays.asList("system","humanist","serif","mono"));allowed.put("text_size",Arrays.asList("compact","standard","large","extra"));allowed.put("thinking_effort",REASONING_EFFORTS);
        for(String key:allowed.keySet())if(values.has(key)&&!allowed.get(key).contains(values.get(key)))throw new IllegalArgumentException("Réglage invalide : "+key);
        if(values.has("thinking_by_model")){
            Object raw=values.get("thinking_by_model");if(!(raw instanceof JSONObject))throw new IllegalArgumentException("Réglage invalide : thinking_by_model");
            JSONObject choices=(JSONObject)raw;if(choices.length()>512)throw new IllegalArgumentException("Réglage invalide : thinking_by_model");
            Iterator<String> models=choices.keys();while(models.hasNext()){
                String model=models.next();if(model.trim().isEmpty()||model.length()>512||model.chars().anyMatch(c->c<32)||!REASONING_EFFORTS.contains(choices.get(model)))throw new IllegalArgumentException("Réglage invalide : thinking_by_model");
            }
        }
        for(String key:new String[]{"thinking","sidebar_collapsed"})if(values.has(key))Json.bool(values,key,false);if(values.has("corrector_text"))Json.string(values,"corrector_text",0,100000);
        JSONObject prefs=settings.optJSONObject("preferences");if(prefs==null)prefs=new JSONObject();Iterator<String> keys=values.keys();while(keys.hasNext()){String key=keys.next();prefs.put(key,values.get(key));}settings.put("preferences",prefs);store.write(identity+".settings",settings);return Json.object("saved",true);
    }
    private JSONObject saveDraft(JSONObject body)throws Exception {Object draft=body.opt("draft");if(draft==null||draft==JSONObject.NULL){store.delete(identity+".draft");return Json.object("saved",true);}if(!(draft instanceof JSONObject))throw new IllegalArgumentException("Brouillon invalide.");JSONObject value=(JSONObject)draft;Json.keys(value,"id","project","title","text","revision");for(String key:new String[]{"id","project"})if(!Json.string(value,key,32,32).matches("[0-9a-f]{32}"))throw new IllegalArgumentException("Identifiant de brouillon invalide.");Json.string(value,"title",0,180);Json.string(value,"text",0,500000);Object revision=value.opt("revision");if(!(revision instanceof Integer||revision instanceof Long)||((Number)revision).longValue()<1)throw new IllegalArgumentException("Révision du brouillon invalide.");if(Json.bytes(value).length>2*1024*1024)throw new IllegalArgumentException("Brouillon trop volumineux.");store.write(identity+".draft",Json.object("draft",value));return Json.object("saved",true);}
    JSONObject config(){return Json.object("key",key,"model",remote.state().optString("model"),"version",BuildConfig.VERSION_NAME,"storage",identity,"platform","android");}
    @Override public void close(){updates.close();remote.close();}
}
