package net.karenax.fred;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicBoolean;

/** Debug source set only: an explicit test transport that cannot contact any server. */
final class DemoTransport {
    private final SecureStore store;
    private final DemoWorkspace workspace;
    private JSONObject history;
    private int revision;
    private String generation="";
    private boolean restored=false;
    private volatile AtomicBoolean cancelled=new AtomicBoolean();
    private final java.util.concurrent.atomic.AtomicInteger calls=new java.util.concurrent.atomic.AtomicInteger();
    DemoTransport(SecureStore store)throws Exception {this.store=store;workspace=new DemoWorkspace(store);JSONObject saved=store.read("demo.server-history");if(saved!=null){history=saved.optJSONObject("history");revision=saved.optInt("revision");}}
    static JSONObject profile(){String key=android.util.Base64.encodeToString(new byte[32],android.util.Base64.NO_WRAP);char[] fake=new char[43];java.util.Arrays.fill(fake,'A');return Json.object("url","wireguard://10.77.0.1:8766","transport","wireguard","protocol",3,"client_name","Démonstration locale · aucun serveur contacté","token","qwen_0000000000000000_"+new String(fake),"wireguard",Json.object("private_key",key,"server_public_key",key,"preshared_key",key,"address","10.77.0.2/32","endpoint","demo.invalid:51820"));}
    int requestCount(){return calls.get();}
    Remote.Response open(String path,byte[] raw,String requestId)throws Exception {calls.incrementAndGet();JSONObject body=raw==null?new JSONObject():new JSONObject(new String(raw,StandardCharsets.UTF_8));
        switch(path){
            case "/v1/models":return response(Json.object("object","list","data",new JSONArray().put(Json.object("id","fred-demo","object","model","capabilities",Json.object("images",true,"files",new JSONArray().put("txt").put("md").put("pdf").put("docx"),"thinking",true,"reasoning_efforts",new JSONArray().put("none").put("low").put("medium").put("high"),"max_file_bytes",2097152)))));
            case "/v1/status":return response(Json.object("status","ready","model","fred-demo","context_window",32768,"max_context_tokens",32768,"model_loaded",true));
            case "/v1/context":return response(Json.object("tokens",100,"prompt_tokens",100,"used",100,"limit",32768,"capacity",32768,"estimated",false,"context_window",32768,"max_tokens",16384,"available",32668,"remaining",32668,"fits",true));
            case "/v1/history":return history(raw==null?null:body);
            case "/v1/workspace":return response(workspace.get());
            case "/v1/workspace/action":return response(workspace.action(body));
            case "/v1/cancel":cancelled.set(true);return response(Json.object("cancelled",true));
            case "/v1/chat/completions":return chat(body);
            default:return new Remote.Response(404,"application/json",new ByteArrayInputStream(Json.bytes(Json.object("error",Json.object("message","Route de démonstration inconnue.")))));
        }
    }
    private synchronized Remote.Response history(JSONObject body)throws Exception {
        if(body!=null&&body.optBoolean("demo_restore")){
            history=HistorySync.validate(body.getJSONObject("history"));revision++;generation=Json.id();restored=true;
            store.write("demo.server-history",Json.object("history",history,"revision",revision));
        }else if(body!=null){
            if(!HistorySync.RESET_ID.equals(body.optString("reset_id")))throw new IllegalArgumentException("Réinitialisation invalide.");
            if(!generation.isEmpty()&&!generation.equals(body.optString("generation")))return new Remote.Response(409,"application/json",new ByteArrayInputStream(Json.bytes(Json.object("error",Json.object("code","restore_generation_changed","message","Serveur restauré : reprise explicite nécessaire.")))));
            if(!String.valueOf(revision).equals(body.optString("revision")))return new Remote.Response(409,"application/json",new ByteArrayInputStream(Json.bytes(Json.object("error",Json.object("message","Historique de test modifié.")))));
            history=HistorySync.validate(body.getJSONObject("history"));revision++;store.write("demo.server-history",Json.object("history",history,"revision",revision));
        }
        return response(Json.object("history",history,"revision",String.valueOf(revision),"reset_id",HistorySync.RESET_ID,"generation",generation,"restored",restored));
    }
    private Remote.Response chat(JSONObject body)throws Exception {String text="Cette réponse de démonstration confirme que le client Android fonctionne. Vous pouvez poursuivre avec les projets, les documents et les tâches.";String reason="Je vérifie le fonctionnement local du client téléphone et tablette.";if(!body.optBoolean("stream")||body.optBoolean("demo_json_fallback"))return response(Json.object("id","demo","model","fred-demo","choices",new JSONArray().put(Json.object("index",0,"message",Json.object("role","assistant","content",text),"finish_reason","stop"))));
        PipedInputStream input=new PipedInputStream(16384);PipedOutputStream output=new PipedOutputStream(input);AtomicBoolean cancel=new AtomicBoolean();cancelled=cancel;new Thread(()->{try(OutputStream stream=output){if(!"none".equals(body.optString("reasoning_effort","none"))){writeEvent(stream,"reasoning_content",reason);Thread.sleep(80);}for(String word:text.split(" ")){if(cancel.get())break;writeEvent(stream,"content",word+" ");Thread.sleep(35);}stream.write(("data: "+Json.object("choices",new JSONArray().put(Json.object("index",0,"delta",new JSONObject(),"finish_reason",cancel.get()?"cancelled":"stop")))+"\n\ndata: [DONE]\n\n").getBytes(StandardCharsets.UTF_8));stream.flush();}catch(Exception ignored){}},"fred-demo-stream").start();return new Remote.Response(200,"text/event-stream",input);
    }
    private static void writeEvent(OutputStream stream,String key,String text)throws IOException {stream.write(("data: "+Json.object("id","demo","choices",new JSONArray().put(Json.object("index",0,"delta",Json.object(key,text))))+"\n\n").getBytes(StandardCharsets.UTF_8));stream.flush();}
    private static Remote.Response response(JSONObject value){return new Remote.Response(200,"application/json",new ByteArrayInputStream(Json.bytes(value)));}
}
