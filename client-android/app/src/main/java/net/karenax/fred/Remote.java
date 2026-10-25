package net.karenax.fred;

import android.content.Context;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.*;

/** Remote credentials stay here. URLs and credentials are captured as one transport snapshot. */
final class Remote implements AutoCloseable {
    static final class HttpError extends IOException {final int status;final JSONObject body;HttpError(int status,JSONObject body){super(body.optJSONObject("error")==null?"Erreur HTTP "+status:body.optJSONObject("error").optString("message","Erreur HTTP "+status));this.status=status;this.body=body;} }
    static final class Response implements AutoCloseable {final int status;final String type;final InputStream input;final HttpURLConnection connection;Response(HttpURLConnection connection)throws IOException{this.connection=connection;status=connection.getResponseCode();type=connection.getContentType();InputStream raw=status>=400?connection.getErrorStream():connection.getInputStream();input=raw==null?new ByteArrayInputStream(new byte[0]):raw;}Response(int status,String type,InputStream input){this.status=status;this.type=type;this.input=input;connection=null;}public void close(){try{input.close();}catch(IOException ignored){}if(connection!=null)connection.disconnect();} }
    private final Context context;
    final JSONObject profile;
    final AtomicInteger active=new AtomicInteger();
    private final AtomicBoolean checking=new AtomicBoolean();
    private final Set<HttpURLConnection> connections=Collections.synchronizedSet(new HashSet<>());
    private volatile boolean closed=false,connected=false,reachable=false,connectionRequired;
    private volatile String endpoint,model="",code="connecting",error="Connexion au serveur IA…";
    private volatile JSONArray models=new JSONArray();
    private volatile JSONObject modelCatalog=Json.object("object","list","data",new JSONArray()),stream=new JSONObject();
    private volatile boolean catalogReady=false;
    private volatile JSONObject diagnostic=new JSONObject();
    private final AtomicBoolean refreshingDiagnostic=new AtomicBoolean();
    private volatile double checkedAt=0,lastContact=0;
    private int attempts=0,bridgeStarts=0;
    private WireGuardBridge bridge;
    private final DemoTransport demo;
    Remote(Context context,JSONObject profile,JSONObject settings,boolean demo,SecureStore store)throws Exception {this.context=context;this.profile=profile==null?null:Json.copy(profile);this.demo=BuildConfig.DEBUG&&demo?new DemoTransport(store):null;endpoint=this.demo!=null?Profile.HTTPS:settings.optString("endpoint",profile==null?Profile.HTTPS:profile.optJSONObject("wireguard").optString("endpoint"));connectionRequired=profile==null||this.demo==null&&!settings.optBoolean("connection_selected",false);if(profile==null){code="profile_required";error="Importez votre accès personnel.";}else if(connectionRequired){code="connection_selection_required";error="Choisissez le mode de connexion.";}}
    boolean hasProfile(){return profile!=null;}
    int debugRequestCount(){return BuildConfig.DEBUG&&demo!=null?demo.requestCount():0;}
    boolean available(){return !closed&&!connectionRequired&&hasProfile()&&(connected||reachable&&("model_unloaded".equals(code)||"no_models".equals(code)));}
    synchronized JSONObject state(){JSONObject result=Json.object("connection_required",connectionRequired,"connected",connected,"reachable",reachable,"model",model,"models",models,"error",error,"code",code,"endpoint",endpoint,"automatic",false,"transport",Profile.HTTPS.equals(endpoint)?"https":"wireguard","checked_at",checkedAt,"checking",checking.get(),"attempts",attempts,"bridge_starts",bridgeStarts,"last_contact",lastContact,"active_requests",active.get(),"events",new JSONArray(),"stream",stream);Iterator<String> keys=diagnostic.keys();while(keys.hasNext()){String key=keys.next();try{result.put(key,diagnostic.get(key));}catch(JSONException ignored){}}return result;}
    void refreshDiagnostic(){WireGuardBridge snapshot;synchronized(this){snapshot=bridge;}if(snapshot==null||!refreshingDiagnostic.compareAndSet(false,true))return;new Thread(()->{try{if(!snapshot.isAlive()){failure("connection_error","Le moteur WireGuard s’est arrêté. Réessayez la connexion.");return;}JSONObject raw=snapshot.status(),safe=new JSONObject();for(String key:new String[]{"handshake","resolved_endpoint","last_handshake_time_sec","rx_bytes","tx_bytes"})if(raw.has(key))safe.put(key,raw.get(key));synchronized(this){if(bridge==snapshot)diagnostic=safe;}}catch(JSONException ignored){}finally{refreshingDiagnostic.set(false);}},"fred-connection-status").start();}
    synchronized String endpoint(){return endpoint;}
    synchronized void select(String value){if(!hasProfile())throw new IllegalArgumentException("Importez votre accès personnel.");if(active.get()>0||checking.get())throw new IllegalArgumentException("Attendez la fin de la requête avant de changer de connexion.");String selected=Profile.HTTPS.equals(value)?value:Profile.endpoint(value);if(bridge!=null){bridge.close();bridge=null;}diagnostic=new JSONObject();endpoint=selected;connectionRequired=false;connected=false;reachable=false;models=new JSONArray();modelCatalog=Json.object("object","list","data",new JSONArray());catalogReady=false;model="";code="connecting";error="Connexion au serveur IA…";checkedAt=0;}
    Response open(String path,byte[] body,String requestId)throws Exception {
        if(closed)throw new IOException("Client fermé.");if(!path.startsWith("/v1/")||path.contains("\\")||path.contains("\r")||path.contains("\n")||path.contains("?")||path.contains("#")||path.contains(".."))throw new IllegalArgumentException("Route API invalide.");
        if(demo!=null)return demo.open(path,body,requestId);
        String base,header,value;
        synchronized(this){if(!hasProfile())throw new IllegalArgumentException("Importez votre accès personnel.");if(connectionRequired)throw new IllegalArgumentException("Choisissez le mode de connexion.");if(Profile.HTTPS.equals(endpoint)){base=Profile.HTTPS;header="Authorization";value="Bearer "+profile.getString("token");}else{if(bridge!=null&&!bridge.isAlive()){bridge.close();bridge=null;}if(bridge==null){bridge=new WireGuardBridge(context,profile,endpoint);bridgeStarts++;}base=bridge.getBaseUrl();header="X-Qwen-Bridge";value=bridge.getBridgeKey();}}
        HttpURLConnection connection=(HttpURLConnection)new URL(base+path).openConnection();connections.add(connection);connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(path.equals("/v1/device")?3000:30000);connection.setReadTimeout(path.equals("/v1/chat/completions")?900000:path.equals("/v1/workspace/action")||path.equals("/v1/history")?60000:path.equals("/v1/device")?3000:30000);connection.setRequestProperty(header,value);connection.setRequestProperty("User-Agent","AccesServeurKiara/"+BuildConfig.VERSION_NAME+" (Android)");connection.setRequestProperty("X-Fred-Agent-Protocol","4");connection.setRequestProperty("Content-Type","application/json");connection.setRequestProperty("Accept",body!=null?"application/json, text/event-stream":"application/json");if(requestId!=null&&requestId.matches("[A-Za-z0-9_-]{1,128}"))connection.setRequestProperty("X-Qwen-Request",requestId);
        try{if(body!=null){connection.setRequestMethod("POST");connection.setDoOutput(true);connection.setFixedLengthStreamingMode(body.length);try(OutputStream out=connection.getOutputStream()){out.write(body);}}Response response=new Response(connection);if(response.status>=300&&response.status<400){response.close();throw new HttpError(502,Json.object("error",Json.object("code","redirect_blocked","message","Le serveur a demandé une redirection ; elle a été refusée.")));}lastContact=System.currentTimeMillis()/1000d;return response;}catch(Exception e){connections.remove(connection);connection.disconnect();if(e instanceof HttpError)throw e;failure("connection_error","Connexion au serveur IA interrompue. Vérifiez le réseau puis réessayez.");throw e;}
    }
    void finished(Response response){connections.remove(response.connection);response.close();}
    private double deviceReportedAt=0;
    private void reportDevice()throws Exception {
        double now=System.currentTimeMillis()/1000d;
        if(demo!=null||now-deviceReportedAt<60)return;
        deviceReportedAt=now;
        String kind=context.getResources().getConfiguration().smallestScreenWidthDp>=600?"tablet":"phone";
        try{json("/v1/device",Json.object("kind",kind,"version",BuildConfig.VERSION_NAME,"transport",Profile.HTTPS.equals(endpoint)?"https":"wireguard","agent_protocol",4));}
        catch(HttpError e){if(e.status==401||e.status==403)throw e;}
        catch(Exception ignored){}
    }
    JSONObject json(String path,JSONObject body)throws Exception {active.incrementAndGet();Response response=null;try{response=open(path,body==null?null:Json.bytes(body),null);byte[] raw=SecureStore.readBounded(response.input,12*1024*1024);JSONObject result=new JSONObject(new String(raw,StandardCharsets.UTF_8));if(response.status!=200){inspectError(result);throw new HttpError(response.status,result);}return result;}finally{if(response!=null)finished(response);active.decrementAndGet();}}
    JSONObject check(){if(connectionRequired||closed||!hasProfile()||active.get()>0||!checking.compareAndSet(false,true))return state();try{attempts++;JSONObject result=json("/v1/models",null);reportDevice();acceptModels(result);}
        catch(HttpError e){JSONObject detail=e.body.optJSONObject("error");code=detail==null?"http_"+e.status:detail.optString("code","http_"+e.status);error=detail==null?"Le serveur a répondu avec une erreur.":detail.optString("message","Le serveur a répondu avec une erreur.");reachable=!Arrays.asList("wireguard_unreachable","tunnel_request_failed").contains(code);connected=false;models=new JSONArray();modelCatalog=Json.object("object","list","data",new JSONArray());catalogReady=false;model="";}
        catch(Exception e){failure("connection_error",safeMessage(e));}
        finally{checkedAt=System.currentTimeMillis()/1000d;checking.set(false);}return state();}
    /** Keep only public catalogue fields; provider credentials never reach the WebView. */
    synchronized void acceptModels(JSONObject value)throws JSONException {
        JSONArray data=value.optJSONArray("data");if(data==null||data.length()>1000)throw new IllegalArgumentException("Liste des modèles invalide.");
        JSONArray found=new JSONArray(),rows=new JSONArray();LinkedHashSet<String> ids=new LinkedHashSet<>(),availableIds=new LinkedHashSet<>();
        for(int i=0;i<data.length();i++){
            JSONObject row=data.optJSONObject(i);if(row==null||!(row.opt("id") instanceof String))continue;
            String id=row.getString("id");if(id.trim().isEmpty()||id.length()>512||!ids.add(id))continue;
            JSONObject safe=Json.object("id",id,"object","model","capabilities",row.optJSONObject("capabilities")==null?new JSONObject():Json.copy(row.getJSONObject("capabilities")));
            for(String key:new String[]{"name","label","provider"})if(row.opt(key) instanceof String&&row.getString(key).length()<=512)safe.put(key,row.getString(key));
            if(row.has("available"))safe.put("available",row.opt("available") instanceof Boolean&&row.getBoolean("available"));
            rows.put(safe);if(safe.getJSONObject("capabilities").optBoolean("embedding",false))continue;
            found.put(id);if(safe.optBoolean("available",true))availableIds.add(id);
        }
        JSONObject safe=Json.object("object","list","data",rows);
        for(String key:new String[]{"default_model","source"})if(value.opt(key) instanceof String&&value.getString(key).length()<=512)safe.put(key,value.getString(key));
        models=found;modelCatalog=safe;catalogReady=true;reachable=true;
        String preferred=safe.optString("default_model");
        if(!availableIds.isEmpty()){if(availableIds.contains(preferred))model=preferred;else if(!availableIds.contains(model))model=availableIds.iterator().next();connected=true;code="ready";error="";}
        else{boolean embeddings=false;for(int i=0;i<rows.length();i++){JSONObject row=rows.getJSONObject(i);if(row.getJSONObject("capabilities").optBoolean("embedding",false)&&row.optBoolean("available",true))embeddings=true;}connected=embeddings;model="";code=embeddings?"ready":found.length()==0?"no_models":"model_unloaded";error=embeddings?"":found.length()==0?"Serveur joint, mais aucun modèle accessible.":"Serveur joint, mais les modèles sont indisponibles. Choisissez un modèle après leur réactivation.";}
    }
    boolean hasCatalogue(){return catalogReady;}
    JSONObject modelCatalog(){return Json.copy(modelCatalog);}
    JSONArray modelRows()throws JSONException {return modelCatalog().getJSONArray("data");}
    void inspectError(JSONObject result){JSONObject detail=result.optJSONObject("error");if(detail!=null){if("model_unloaded".equals(detail.optString("code"))&&hasAvailableAlternate())return;failure(detail.optString("code"),detail.optString("message","Serveur indisponible."));}}
    private boolean hasAvailableAlternate(){JSONObject snapshot=modelCatalog;if(!"hermes".equals(snapshot.optString("source")))return false;JSONArray rows=snapshot.optJSONArray("data");if(rows==null)return false;for(int i=0;i<rows.length();i++){JSONObject row=rows.optJSONObject(i);if(row!=null&&!"fred-qwen".equals(row.optString("id"))&&row.optBoolean("available",true))return true;}return false;}
    void failure(String code,String message){if(Arrays.asList("connection_error","gateway_unavailable","access_denied","access_revoked","access_suspended","access_expired","remote_disabled","model_unloaded","no_models","wireguard_unreachable","tunnel_request_failed").contains(code)){this.connected=false;this.reachable=!Arrays.asList("connection_error","wireguard_unreachable","tunnel_request_failed").contains(code);this.code=code;this.error=message;checkedAt=System.currentTimeMillis()/1000d;}}
    synchronized void startStream(){stream=Json.object("phase","requesting","started",System.currentTimeMillis()/1000d,"last_event",System.currentTimeMillis()/1000d,"reasoning_chars",0,"answer_chars",0);}
    synchronized void streamLine(String line){try{stream.put("last_event",System.currentTimeMillis()/1000d);if(line.startsWith(": qwen-queue ")){int position=new JSONObject(line.substring(13)).optInt("position");stream.put("phase",position>0?"queued":"waiting_model");stream.put("position",position);}else if(line.startsWith("data: ")&&!line.equals("data: [DONE]")){JSONObject event=new JSONObject(line.substring(6));JSONObject status=event.optJSONObject("hermes_status");if(status!=null)stream.put("phase",status.optString("phase","working"));if(event.optJSONObject("hermes_approval")!=null)stream.put("phase","approval");JSONObject finalAnswer=event.optJSONObject("hermes_answer");if(finalAnswer!=null&&finalAnswer.opt("text") instanceof String)stream.put("answer_chars",finalAnswer.getString("text").length());JSONArray choices=event.optJSONArray("choices");if(choices==null||choices.length()==0)return;JSONObject choice=choices.getJSONObject(0),delta=choice.optJSONObject("delta");if(delta==null)return;String reasoning=delta.optString("reasoning_content",delta.optString("reasoning")),answer=delta.optString("content");if(!reasoning.isEmpty()){stream.put("reasoning_chars",stream.optInt("reasoning_chars")+reasoning.length());stream.put("phase","thinking");}if(!answer.isEmpty()){stream.put("answer_chars",stream.optInt("answer_chars")+answer.length());stream.put("phase","answering");}if(choice.has("finish_reason")&&!choice.isNull("finish_reason"))stream.put("finish_reason",choice.get("finish_reason"));}}catch(JSONException ignored){} }
    synchronized void endStream(boolean done){try{stream.put("phase",done?"complete":"interrupted");}catch(JSONException ignored){} }
    static String safeMessage(Exception error){if(error instanceof IllegalArgumentException||error instanceof HistorySync.Conflict||error instanceof HttpError)return error.getMessage()==null?"Requête impossible.":error.getMessage();return "Connexion ou stockage indisponible. Réessayez ; les données locales sont conservées.";}
    @Override public synchronized void close(){closed=true;for(HttpURLConnection connection:new ArrayList<>(connections))connection.disconnect();connections.clear();if(bridge!=null){bridge.close();bridge=null;}}
}
