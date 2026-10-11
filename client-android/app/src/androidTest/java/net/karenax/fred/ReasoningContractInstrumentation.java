package net.karenax.fred;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import android.util.Base64;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

/** Real encrypted preference persistence and public reasoning contract through an isolated tunnel. */
public final class ReasoningContractInstrumentation extends Instrumentation {
    private static final String[] EFFORTS={"none","minimal","low","medium","high","xhigh","max","ultra","on"};
    private static final String TEXT="Test synthétique Android : raisonnement sélectionné.";
    private Bundle arguments;
    @Override public void onCreate(Bundle args){super.onCreate(args);arguments=args;start();}
    private static void check(boolean condition){if(!condition)throw new AssertionError("Reasoning contract failed");}
    private static HttpURLConnection request(LoopbackServer local,ClientBackend client,String path,JSONObject body)throws Exception{
        HttpURLConnection connection=(HttpURLConnection)new URL(local.origin()+path).openConnection();
        connection.setConnectTimeout(15000);connection.setReadTimeout(30000);connection.setRequestProperty("Authorization","Bearer "+client.key);
        if(body!=null){connection.setRequestMethod("POST");connection.setDoOutput(true);connection.setRequestProperty("Content-Type","application/json");connection.setRequestProperty("X-Qwen-Request",Json.id());byte[] bytes=Json.bytes(body);connection.setFixedLengthStreamingMode(bytes.length);try(OutputStream out=connection.getOutputStream()){out.write(bytes);}}
        return connection;
    }
    private static JSONObject json(LoopbackServer local,ClientBackend client,String path,JSONObject body,int status)throws Exception{
        HttpURLConnection connection=request(local,client,path,body);
        try{check(connection.getResponseCode()==status);try(InputStream input=status>=400?connection.getErrorStream():connection.getInputStream()){return new JSONObject(new String(SecureStore.readBounded(input,1024*1024),StandardCharsets.UTF_8));}}
        finally{connection.disconnect();}
    }
    private static void preferences(Instrumentation instrumentation,StringBuilder log)throws Exception{
        SecureStore store=new SecureStore(instrumentation.getTargetContext(),"reasoning-contract-test-vault");store.delete("guest.settings");
        try{
            try(ClientBackend client=new ClientBackend(instrumentation.getTargetContext(),store,null,false);LoopbackServer local=new LoopbackServer(instrumentation.getTargetContext(),client)){
                json(local,client,"/client/preferences",Json.object("theme","dark","thinking",true),200);
                for(String effort:EFFORTS){
                    check(json(local,client,"/client/preferences",Json.object("thinking_effort",effort,"thinking",!"none".equals(effort)),200).getBoolean("saved"));
                    check(effort.equals(store.read("guest.settings").getJSONObject("preferences").getString("thinking_effort")));
                }
                JSONObject byModel=Json.object("legacy-provider/Nemotron-fixture","max","fred-model-toggle","on","fred-qwen","low");
                json(local,client,"/client/preferences",Json.object("thinking_effort","max","thinking_by_model",byModel),200);
                // Changing the legacy global preference must preserve each model's independent selection.
                json(local,client,"/client/preferences",Json.object("thinking_effort","low","thinking",true),200);
                check(Json.canonical(store.read("guest.settings").getJSONObject("preferences").getJSONObject("thinking_by_model")).equals(Json.canonical(byModel)));
                check(!new String(store.raw("guest.settings"),StandardCharsets.ISO_8859_1).contains("legacy-provider/Nemotron-fixture"));
                log.append("PASS all nine canonical efforts save exactly; per-model max/on/legacy selections survive other model changes in encrypted storage\n");
                JSONObject full=new JSONObject();for(int i=0;i<512;i++)full.put("legacy-model-"+i,EFFORTS[i%EFFORTS.length]);
                json(local,client,"/client/preferences",Json.object("thinking_by_model",full),200);
                check(store.read("guest.settings").getJSONObject("preferences").getJSONObject("thinking_by_model").length()==512);
                JSONObject boundary=Json.object(new String(new char[512]).replace('\0','x'),"ultra");
                json(local,client,"/client/preferences",Json.object("thinking_by_model",boundary),200);
                json(local,client,"/client/preferences",Json.object("thinking_by_model",byModel),200);
                String revision=store.revision("guest.settings");JSONObject tooMany=Json.copy(full);tooMany.put("extra-model","max");
                Object[] invalidMaps={JSONObject.NULL,true,new JSONArray(),"map",tooMany,Json.object("","max"),Json.object("   ","max"),Json.object("model\n","max"),Json.object(new String(new char[513]).replace('\0','x'),"max"),Json.object("model",JSONObject.NULL),Json.object("model",true),Json.object("model","off"),Json.object("model","MAX")};
                for(Object invalid:invalidMaps){json(local,client,"/client/preferences",Json.object("theme","light","thinking_by_model",invalid),400);check(revision.equals(store.revision("guest.settings")));}
                for(Object invalid:new Object[]{JSONObject.NULL,true,"off","MAX","unknown"}){json(local,client,"/client/preferences",Json.object("thinking_effort",invalid),400);check(revision.equals(store.revision("guest.settings")));}
                json(local,client,"/client/preferences",Json.object("thinking","true"),400);check(revision.equals(store.revision("guest.settings")));
                check("dark".equals(store.read("guest.settings").getJSONObject("preferences").getString("theme")));
                log.append("PASS 512 entries/512-character legacy ID accepted; 19 malformed/oversized preference requests rejected before any encrypted write\n");
            }
            try(ClientBackend reopened=new ClientBackend(instrumentation.getTargetContext(),store,null,false);LoopbackServer local=new LoopbackServer(instrumentation.getTargetContext(),reopened)){
                JSONObject prefs=json(local,reopened,"/client/state",null,200).getJSONObject("preferences");
                check("low".equals(prefs.getString("thinking_effort"))&&prefs.getBoolean("thinking")&&"dark".equals(prefs.getString("theme")));
                JSONObject byModel=prefs.getJSONObject("thinking_by_model");check(byModel.length()==3&&"max".equals(byModel.getString("legacy-provider/Nemotron-fixture"))&&"on".equals(byModel.getString("fred-model-toggle")));
                log.append("PASS canonical per-model preferences survive native backend close/reopen; legacy boolean and appearance preserved\n");
            }
        }finally{store.delete("guest.settings");}
    }
    private void transport(StringBuilder log)throws Exception{
        JSONObject profile=Profile.validate(new JSONObject(new String(Base64.decode(arguments.getString("fred_profile_b64"),Base64.DEFAULT),StandardCharsets.UTF_8)));
        SecureStore store=new SecureStore(getTargetContext(),"reasoning-transport-test-vault");String identity=Profile.identity(profile);
        try(ClientBackend client=new ClientBackend(getTargetContext(),store,profile,false)){
            client.selectMode("wireguard");try(LoopbackServer local=new LoopbackServer(getTargetContext(),client)){
                JSONArray catalogue=json(local,client,"/v1/models",null,200).getJSONArray("data");check(catalogue.length()==4);
                String[][] cases={{"none","low","medium","high"},{"none","on"},{"none","minimal","low","medium","high","xhigh","max","ultra"},{}};
                String[] modes={"effort","toggle","effort","none"};JSONArray messages=new JSONArray().put(Json.object("role","user","content",TEXT));
                for(int index=0;index<catalogue.length();index++){
                    JSONObject row=catalogue.getJSONObject(index),caps=row.getJSONObject("capabilities");String model=row.getString("id");
                    check(modes[index].equals(caps.getString("reasoning_mode"))&&new JSONArray(cases[index]).toString().equals(caps.getJSONArray("reasoning_efforts").toString()));
                    for(String effort:cases[index].length==0?new String[]{null}:cases[index]){
                        JSONObject context=Json.object("model",model,"messages",messages);if(effort!=null)context.put("reasoning_effort",effort);
                        check(json(local,client,"/v1/context",context,200).getBoolean("fits"));
                        JSONObject body=Json.copy(context);body.put("stream",true);body.put("conversation_id",Json.id());
                        HttpURLConnection connection=request(local,client,"/v1/chat/completions",body);
                        try{
                            check(connection.getResponseCode()==200&&connection.getContentType().startsWith("text/event-stream"));boolean done=false;StringBuilder answer=new StringBuilder();
                            try(BufferedReader input=new BufferedReader(new InputStreamReader(connection.getInputStream(),StandardCharsets.UTF_8))){String line;while((line=input.readLine())!=null){if(line.equals("data: [DONE]"))done=true;else if(line.startsWith("data: "))answer.append(new JSONObject(line.substring(6)).getJSONArray("choices").getJSONObject(0).getJSONObject("delta").optString("content"));}}
                            check(done&&answer.toString().contains("Connexion Android WireGuard vérifiée"));
                        }finally{connection.disconnect();}
                    }
                }
                log.append("PASS public native effort/toggle/automatic metadata and all 15 exact selected reasoning combinations forward unchanged in context and SSE chat over authenticated WireGuard\n");
                for(String model:new String[]{"fred-model-toggle","fred-model-auto"})check("reasoning_effort_unavailable".equals(json(local,client,"/v1/context",Json.object("model",model,"reasoning_effort","max","messages",messages),400).getJSONObject("error").getString("code")));
                check(client.remote.state().getBoolean("connected"));log.append("PASS explicit unsupported reasoning errors preserve the native model connection\n");
            }
        }finally{store.delete(identity+".settings");}
    }
    @Override public void onStart(){Bundle result=new Bundle();StringBuilder log=new StringBuilder();try{
        preferences(this,log);if(arguments!=null&&arguments.containsKey("fred_profile_b64"))transport(log);
        result.putString("stream",log+"ALL REASONING CONTRACT CHECKS PASSED\n");result.putBoolean("passed",true);finish(Activity.RESULT_OK,result);
    }catch(Throwable error){result.putString("stream",log+"FAIL "+error.getClass().getSimpleName()+"\n");result.putBoolean("passed",false);finish(Activity.RESULT_CANCELED,result);}}
}
