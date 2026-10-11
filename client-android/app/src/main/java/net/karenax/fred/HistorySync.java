package net.karenax.fred;

import org.json.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.ReentrantLock;

final class HistorySync {
    static final String RESET_ID="20261006-remove-assistants";
    static class Conflict extends Exception { Conflict(String message){super(message);} }
    private final SecureStore store;
    private final Remote remote;
    private final String name;
    private volatile JSONObject meta;
    private volatile JSONObject status=Json.object("server_synced",false,"pending",true,"message","Copie locale chargée · connexion au serveur nécessaire.");
    private final AtomicBoolean scheduled=new AtomicBoolean();
    private final ReentrantLock workerLock=new ReentrantLock();
    HistorySync(SecureStore store,Remote remote,String identity) throws Exception {this.store=store;this.remote=remote;name=identity+".history";try{meta=store.read(name+".sync");}catch(Exception ignored){meta=null;}if(meta==null)meta=new JSONObject();}
    static JSONObject empty(){String id=Json.id();return Json.object("conversations",new JSONArray().put(Json.object("id",id,"title","Nouvelle conversation","messages",new JSONArray())),"currentId",id);}
    synchronized JSONObject read() throws Exception {JSONObject history;try{history=store.read(name);if(history!=null)validate(history);}catch(Exception e){throw new IllegalStateException("Historique illisible : le fichier original est conservé. Exportez vos conversations avant récupération.");}JSONObject result=Json.object("history",history,"revision",store.revision(name));append(result,status);return result;}
    JSONObject status(){return Json.copy(status);}
    synchronized JSONObject write(JSONObject history,String revision) throws Exception {validate(history);if(!store.revision(name).equals(revision))throw new Conflict("Historique modifié par une autre fenêtre. Rechargez le client.");String saved=store.write(name,history);status=Json.object("server_synced",false,"pending",true,"message","Copie locale chiffrée enregistrée · synchronisation en attente.");schedule();JSONObject result=Json.object("saved",true,"revision",saved);append(result,status);return result;}
    synchronized JSONObject recover(JSONObject history) throws Exception {validate(history);try{read();}catch(IllegalStateException e){byte[] raw=store.raw(name);if(raw==null)throw e;String backup=name+".unreadable-"+Json.id().substring(0,12);store.writeRaw(backup,raw);return Json.object("saved",true,"revision",store.write(name,history),"backup",backup);}throw new IllegalArgumentException("L’historique est lisible. Rechargez le client pour éviter de l’écraser.");}
    JSONObject synchronize(JSONObject initial) throws Exception {workerLock.lock();try{synchronized(this){return synchronizeLocked(initial);}}finally{workerLock.unlock();}}
    private JSONObject synchronizeLocked(JSONObject initial) throws Exception {
        if(!remote.hasProfile())return Json.object("history",initial==null?empty():validate(initial),"revision","","server_synced",false,"pending",true,"message","Importez votre accès personnel.");
        try {
            for(int attempt=0;attempt<3;attempt++) {
                JSONObject local=read(),server=remote.json("/v1/history",null);JSONObject history=local.optJSONObject("history"),serverHistory=server.optJSONObject("history");int conflicts=0;
                if(!RESET_ID.equals(server.optString("reset_id")))throw new IllegalArgumentException("Mettre à jour le serveur avant de synchroniser cet historique.");
                if(history!=null&&!server.optString("generation").isEmpty()&&!server.optString("generation").equals(meta.optString("generation"))&&(!meta.optString("generation").isEmpty()||server.optBoolean("restored"))){status=Json.object("server_synced",false,"pending",true,"needs_merge",true,"requires_restore_ack",true,"message","État serveur différent : confirmer sa reprise. Votre copie locale sera conservée.");append(local,status);return local;}
                if(serverHistory!=null)validate(serverHistory);
                if(history==null){history=serverHistory!=null?serverHistory:validate(initial==null?empty():initial);if(serverHistory!=null&&initial!=null&&hasMessages(initial)){Merge merged=merge(validate(initial),serverHistory,new JSONObject());history=merged.history;conflicts=merged.conflicts;}}
                else if(serverHistory!=null&&!local.optString("revision").equals(meta.optString("local_revision"))){if(!server.optString("revision").equals(meta.optString("server_revision"))){Merge merged=merge(history,serverHistory,meta.optJSONObject("base")==null?new JSONObject():meta.optJSONObject("base"));history=merged.history;conflicts=merged.conflicts;}}
                else if(serverHistory!=null)history=serverHistory;
                String serverRevision=server.optString("revision");
                if(!same(history,serverHistory)){
                    try { JSONObject saved=remote.json("/v1/history",Json.object("history",history,"revision",serverRevision,"reset_id",RESET_ID,"generation",server.optString("generation")));serverRevision=saved.getString("revision"); }
                    catch(Remote.HttpError error){if(error.status==409&&attempt<2)continue;throw error;}
                }
                String revision=local.optString("revision");if(!same(history,local.optJSONObject("history")))revision=store.write(name,history);
                meta=Json.object("server_revision",serverRevision,"local_revision",revision,"base",fingerprints(history),"reset_id",RESET_ID,"generation",server.optString("generation"));store.write(name+".sync",meta);
                status=Json.object("server_synced",true,"pending",false,"message","Historique enregistré sur le serveur · copie locale chiffrée.","merged",conflicts);
                JSONObject result=Json.object("history",history,"revision",revision);append(result,status);return result;
            }
            throw new Conflict("Historique modifié sur un autre appareil. Réessayez la synchronisation.");
        }catch(Exception error){status=Json.object("server_synced",false,"pending",true,"message","Copie locale conservée · "+Remote.safeMessage(error));throw error;}
    }
    void schedule(){if(!remote.available()||!meta.has("server_revision")||status.optBoolean("needs_merge")||!scheduled.compareAndSet(false,true))return;new Thread(()->{
        if(!workerLock.tryLock()){scheduled.set(false);return;}
        try {
            while(remote.available()) {
                JSONObject snapshot;String serverRevision;
                synchronized(this){snapshot=read();serverRevision=meta.optString("server_revision");if(snapshot.optJSONObject("history")==null||snapshot.optString("revision").equals(meta.optString("local_revision")))break;}
                // Upload only: the WebView owns its current local revision until an explicit sync.
                JSONObject saved=remote.json("/v1/history",Json.object("history",snapshot.getJSONObject("history"),"revision",serverRevision,"reset_id",RESET_ID,"generation",meta.optString("generation")));
                synchronized(this){meta=Json.object("server_revision",saved.getString("revision"),"local_revision",snapshot.getString("revision"),"base",fingerprints(snapshot.getJSONObject("history")),"reset_id",RESET_ID,"generation",meta.optString("generation"));store.write(name+".sync",meta);boolean pending=!store.revision(name).equals(snapshot.getString("revision"));status=Json.object("server_synced",!pending,"pending",pending,"message",pending?"Synchronisation en cours…":"Historique enregistré sur le serveur · copie locale chiffrée.");}
            }
        }catch(Exception error){status=Json.object("server_synced",false,"pending",true,"needs_merge",error instanceof Remote.HttpError&&((Remote.HttpError)error).status==409,"message","Copie locale conservée · synchronisation en attente : "+Remote.safeMessage(error));}
        finally{workerLock.unlock();scheduled.set(false);}
    },"fred-history-sync").start();}
    JSONObject flush(){schedule();return status();}
    JSONObject acknowledgeRestore(boolean confirmed)throws Exception {if(!confirmed)throw new IllegalArgumentException("Confirmez la reprise de l’historique du serveur.");workerLock.lock();try{synchronized(this){if(!status.optBoolean("requires_restore_ack"))throw new IllegalArgumentException("Resynchronisez le client avant de confirmer la reprise.");JSONObject local=read(),server=remote.json("/v1/history",null);if(!RESET_ID.equals(server.optString("reset_id"))||server.optString("generation").isEmpty())throw new IllegalArgumentException("État serveur incompatible.");String backup=name+".before-restore-"+Json.id();if(local.optJSONObject("history")!=null)store.write(backup,local.getJSONObject("history"));JSONObject history=server.optJSONObject("history");if(history==null)history=empty();validate(history);String revision=store.write(name,history);meta=Json.object("server_revision",server.optString("revision"),"local_revision",revision,"base",fingerprints(history),"reset_id",RESET_ID,"generation",server.optString("generation"));store.write(name+".sync",meta);status=Json.object("server_synced",true,"pending",false,"message","Historique serveur repris ; copie précédente chiffrée conservée.","restore_backup",backup);JSONObject result=Json.object("history",history,"revision",revision);append(result,status);return result;}}finally{workerLock.unlock();}}
    private static void append(JSONObject target,JSONObject source){source.keys().forEachRemaining(k->{try{target.put(k,source.get(k));}catch(JSONException e){throw new IllegalArgumentException(e);}});}
    private static boolean hasMessages(JSONObject history)throws JSONException {JSONArray rows=history.getJSONArray("conversations");for(int i=0;i<rows.length();i++)if(rows.getJSONObject(i).getJSONArray("messages").length()>0)return true;return false;}
    private static boolean same(JSONObject a,JSONObject b)throws JSONException {return a==null?b==null:b!=null&&Json.canonical(a).equals(Json.canonical(b));}
    static JSONObject fingerprints(JSONObject history)throws JSONException {JSONObject hashes=new JSONObject();JSONArray rows=history.getJSONArray("conversations");for(int i=0;i<rows.length();i++){JSONObject row=rows.getJSONObject(i);hashes.put(row.getString("id"),Json.hash(Json.canonical(row).getBytes(StandardCharsets.UTF_8)));}return hashes;}
    static final class Merge { final JSONObject history;final int conflicts;Merge(JSONObject history,int conflicts){this.history=history;this.conflicts=conflicts;} }
    static Merge merge(JSONObject local,JSONObject server,JSONObject base)throws JSONException {
        LinkedHashMap<String,JSONObject> left=rows(local),right=rows(server);LinkedHashSet<String> ids=new LinkedHashSet<>(left.keySet());ids.addAll(right.keySet());JSONObject lh=fingerprints(local),rh=fingerprints(server);JSONArray rows=new JSONArray();String current=local.getString("currentId");int conflicts=0;
        for(String id:ids){JSONObject l=left.get(id),r=right.get(id);String before=base.optString(id,""),selected=null;
            if(same(l,r)){if(l!=null)rows.put(Json.copy(l));}
            else if(!before.isEmpty()&&before.equals(lh.optString(id))){if(r!=null)rows.put(Json.copy(r));}
            else if(!before.isEmpty()&&before.equals(rh.optString(id))){if(l!=null)rows.put(Json.copy(l));}
            else if(l==null){if(r!=null)rows.put(Json.copy(r));}
            else if(r==null)rows.put(Json.copy(l));
            else{JSONObject reconciled=authoritativeTurns(l,r);if(reconciled!=null){rows.put(reconciled);continue;}rows.put(Json.copy(r));JSONObject branch=Json.copy(l);String branchId=Json.id(),title=branch.getString("title");branch.put("id",branchId);branch.put("title",title.substring(0,Math.min(103,title.length()))+" (copie locale)");branch.remove("server_revision");rows.put(branch);conflicts++;if(current.equals(id))current=branchId;}
        }
        if(rows.length()==0)throw new IllegalArgumentException("Conserver au moins une conversation.");boolean found=false;for(int i=0;i<rows.length();i++)if(current.equals(rows.getJSONObject(i).getString("id")))found=true;if(!found)current=rows.getJSONObject(0).getString("id");return new Merge(validate(Json.object("conversations",rows,"currentId",current)),conflicts);
    }
    private static LinkedHashMap<String,JSONObject> rows(JSONObject history)throws JSONException {LinkedHashMap<String,JSONObject> result=new LinkedHashMap<>();JSONArray array=history.getJSONArray("conversations");for(int i=0;i<array.length();i++){JSONObject row=array.getJSONObject(i);result.put(row.getString("id"),row);}return result;}
    private static JSONObject comparableMessage(JSONObject value)throws JSONException {JSONObject result=Json.copy(value);if(result.optString("reasoning_content").isEmpty())result.remove("reasoning_content");if(!result.optBoolean("interrupted"))result.remove("interrupted");return result;}
    static JSONObject authoritativeTurns(JSONObject local,JSONObject server)throws JSONException {
        for(String key:new String[]{"id","project_id","document_id","archived","model"})if(!Objects.equals(local.opt(key),server.opt(key)))return null;
        JSONArray left=local.getJSONArray("messages"),right=server.getJSONArray("messages");if(left.length()>right.length())return null;boolean changed=false;
        for(int i=0;i<left.length();i++){JSONObject message=left.getJSONObject(i),target=right.getJSONObject(i);if(same(message,target))continue;String turn=message.optString("turn_id");if(!turn.isEmpty()&&turn.equals(target.optString("turn_id"))&&"assistant".equals(message.optString("role"))&&"assistant".equals(target.optString("role"))&&!target.optBoolean("interrupted")){changed=true;continue;}if(!same(comparableMessage(message),comparableMessage(target)))return null;}
        for(int i=left.length();i<right.length();i++){JSONObject message=right.getJSONObject(i);String turn=message.optString("turn_id");if(!"assistant".equals(message.optString("role"))||turn.isEmpty()||i==0||!turn.equals(right.getJSONObject(i-1).optString("turn_id"))||!"user".equals(right.getJSONObject(i-1).optString("role")))return null;changed=true;}
        if(!changed)return null;JSONObject result=Json.copy(local);result.put("messages",new JSONArray(right.toString()));return result;
    }
    static JSONObject validate(JSONObject value)throws JSONException {
        if(value==null)throw new IllegalArgumentException("Historique invalide.");Json.keys(value,"conversations","currentId");JSONArray rows=value.optJSONArray("conversations");if(rows==null||rows.length()<1||rows.length()>200)throw new IllegalArgumentException("Conserver entre 1 et 200 conversations.");Set<String> ids=new HashSet<>();
        for(int i=0;i<rows.length();i++){JSONObject row=rows.getJSONObject(i);Json.keys(row,"id","title","messages","project_id","document_id","server_revision","archived","model");String id=Json.string(row,"id",1,80);if(!ids.add(id))throw new IllegalArgumentException("Identifiant dupliqué.");Json.string(row,"title",1,120);if(row.has("model")&&Json.string(row,"model",1,512).trim().isEmpty())throw new IllegalArgumentException("Modèle invalide.");if(row.has("archived"))Json.bool(row,"archived",false);for(String key:new String[]{"project_id","document_id"})if(row.has(key)&&!row.isNull(key)&&!row.getString(key).matches("[0-9a-f]{32}"))throw new IllegalArgumentException("Projet ou document invalide.");if(row.has("server_revision")){Object rev=row.get("server_revision");if(!(rev instanceof Integer||rev instanceof Long)||((Number)rev).longValue()<0)throw new IllegalArgumentException("Révision invalide.");}JSONArray messages=row.optJSONArray("messages");if(messages==null||messages.length()>1000)throw new IllegalArgumentException("Messages invalides.");for(int j=0;j<messages.length();j++)validateMessage(messages.getJSONObject(j));}
        if(!ids.contains(value.optString("currentId")))throw new IllegalArgumentException("Conversation sélectionnée introuvable.");if(Json.bytes(value).length>9*1024*1024)throw new IllegalArgumentException("Historique limité à 9 Mo. Exportez puis supprimez des conversations.");return value;
    }
    private static void validateMessage(JSONObject message)throws JSONException {
        Json.keys(message,"role","content","reasoning_content","interrupted","attachments","turn_id");String role=message.optString("role");if(!role.equals("user")&&!role.equals("assistant"))throw new IllegalArgumentException("Message texte attendu.");Json.string(message,"content",0,9*1024*1024);if(message.has("reasoning_content"))Json.string(message,"reasoning_content",0,9*1024*1024);if(message.has("interrupted"))Json.bool(message,"interrupted",false);if(message.has("turn_id")&&!Json.string(message,"turn_id",1,128).matches("[A-Za-z0-9_-]{1,128}"))throw new IllegalArgumentException("Identifiant du tour invalide.");
        JSONArray attachments=message.optJSONArray("attachments");if(message.has("attachments")&&attachments==null||attachments!=null&&(attachments.length()>4||attachments.length()>0&&!role.equals("user")))throw new IllegalArgumentException("Pièces jointes invalides.");if(attachments==null)return;
        for(int i=0;i<attachments.length();i++){JSONObject item=attachments.getJSONObject(i);Json.string(item,"name",1,180);if("file".equals(item.optString("kind"))){Json.keys(item,"name","kind","text");Json.string(item,"text",1,50000);}else if("image".equals(item.optString("kind"))){Json.keys(item,"name","kind","url");String url=Json.string(item,"url",1,3*1024*1024);int comma=url.indexOf(',');if(comma<0||!url.substring(0,comma).matches("data:image/(?:png|jpeg|webp);base64"))throw new IllegalArgumentException("Image intégrée attendue.");String encoded=url.substring(comma+1);if(!encoded.matches("[A-Za-z0-9+/]*={0,2}"))throw new IllegalArgumentException("Image encodée invalide.");byte[] data=android.util.Base64.decode(encoded,android.util.Base64.NO_WRAP);boolean png=url.startsWith("data:image/png"),jpg=url.startsWith("data:image/jpeg");boolean valid=png?data.length>=8&&data[0]==(byte)137&&data[1]==80&&data[2]==78&&data[3]==71:jpg?data.length>=3&&data[0]==(byte)255&&data[1]==(byte)216&&data[2]==(byte)255:data.length>=12&&new String(data,0,4,StandardCharsets.US_ASCII).equals("RIFF")&&new String(data,8,4,StandardCharsets.US_ASCII).equals("WEBP");if(!valid||data.length>2*1024*1024)throw new IllegalArgumentException("Image invalide ou supérieure à 2 Mo.");}else throw new IllegalArgumentException("Pièce jointe invalide.");}
    }
}
