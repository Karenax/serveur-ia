package net.karenax.fred;

import android.app.*;
import android.content.*;
import org.json.*;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

/** Real native ASR, AudioRecord lifecycle and authenticated loopback; fixture data only. */
final class ConversationChecks {
    static String permission(Instrumentation test)throws Exception{
        MainActivity activity=(MainActivity)test.startActivitySync(new Intent(test.getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK).putExtra("fred_demo",true));
        Field field=MainActivity.class.getDeclaredField("conversation");field.setAccessible(true);LocalConversation voice=null;long end=System.currentTimeMillis()+20000;
        while(voice==null&&System.currentTimeMillis()<end){voice=(LocalConversation)field.get(activity);Thread.sleep(100);}check(voice!=null,"Controller ready");
        try{
            JSONObject started=new JSONObject(voice.action("{\"action\":\"start\"}"));check(started.optString("phase").equals("permission")&&started.optBoolean("microphone_closed"),"Permission gate before capture: "+started);
            android.accessibilityservice.AccessibilityServiceInfo info=test.getUiAutomation().getServiceInfo();info.flags|=android.accessibilityservice.AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;test.getUiAutomation().setServiceInfo(info);
            android.view.accessibility.AccessibilityNodeInfo deny=null;end=System.currentTimeMillis()+20000;
            while(deny==null&&System.currentTimeMillis()<end){deny=VoiceChecks.denyButton(test.getUiAutomation().getRootInActiveWindow());Thread.sleep(100);}check(deny!=null&&deny.performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK),"Android microphone permission dialog");
            JSONObject value;do{value=new JSONObject(voice.status());if(value.optString("phase").equals("error"))break;Thread.sleep(100);}while(System.currentTimeMillis()<end);
            check(value.optString("phase").equals("error")&&value.optString("message").contains("Microphone refusé")&&value.optBoolean("microphone_closed"),"Permission denial is recoverable and microphone remains closed: "+value);
            return Json.object("passed",true,"permission","Real Android microphone dialog denied; native controller reports recovery and no capture").toString();
        }finally{voice.closeAndWait(10000);test.runOnMainSync(activity::finish);}
    }
    private static Object call(String name,Class<?>[] types,Object...args)throws Exception{Method method=LocalConversation.class.getDeclaredMethod(name,types);method.setAccessible(true);return method.invoke(null,args);}
    private static JSONObject nativeStatus(long engine)throws Exception{return new JSONObject((String)call("nativeStatus",new Class[]{long.class},engine));}
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    private static JSONObject until(LocalConversation voice,String phase,boolean microphoneClosed)throws Exception{
        long end=System.currentTimeMillis()+60000;JSONObject value;
        do{value=new JSONObject(voice.status());if(value.optString("phase").equals(phase)&&value.optBoolean("microphone_closed")==microphoneClosed)return value;if(value.optString("phase").equals("error"))throw new AssertionError(value.toString());Thread.sleep(100);}while(System.currentTimeMillis()<end);
        throw new AssertionError("Controller timeout "+value);
    }
    static String run(Instrumentation test)throws Exception{
        System.loadLibrary("fredvoice");Context context=test.getTargetContext();File folder=new File(context.getFilesDir(),"voice");
        long engine=(Long)call("nativeCreate",new Class[]{String.class,String.class},new File(folder,"ggml-small.bin").getAbsolutePath(),context.getApplicationInfo().nativeLibraryDir);
        JSONObject result=new JSONObject();
        try{
            long end=System.currentTimeMillis()+60000;while(!nativeStatus(engine).optString("phase").equals("listening")&&System.currentTimeMillis()<end)Thread.sleep(100);
            check(nativeStatus(engine).optString("phase").equals("listening"),"Native model load");
            byte[] wave;try(InputStream input=new FileInputStream(new File(folder,"conversation.wav"))){wave=SecureStore.readBounded(input,1024*1024);}
            short[] audio=new short[1600];int start=44;check(new String(wave,36,4,"US-ASCII").equals("data"),"PCM fixture header");
            for(int offset=start;offset<wave.length;offset+=3200){int count=Math.min(1600,(wave.length-offset)/2);for(int i=0;i<count;i++)audio[i]=(short)((wave[offset+2*i]&255)|(wave[offset+2*i+1]<<8));call("nativeFeed",new Class[]{long.class,short[].class,int.class},engine,audio,count);Thread.sleep(100);}
            java.util.Arrays.fill(audio,(short)0);for(int i=0;i<18;i++){call("nativeFeed",new Class[]{long.class,short[].class,int.class},engine,audio,1600);Thread.sleep(100);}
            end=System.currentTimeMillis()+120000;JSONObject value;
            do{value=nativeStatus(engine);if(value.getJSONArray("turns").length()>0)break;Thread.sleep(100);}while(System.currentTimeMillis()<end);
            check(value.getJSONArray("turns").length()>0,"Final utterance after silence");
            JSONObject turn=value.getJSONArray("turns").getJSONObject(0);String text=turn.getString("text").toLowerCase(java.util.Locale.ROOT);check(text.contains("bonjour")&&text.contains("questions"),"French voice recognition: "+text);
            check(value.getString("phase").equals("listening"),"Conversation stays open after utterance");result.put("recognized",turn);
            call("nativeAck",new Class[]{long.class,int.class},engine,turn.getInt("id"));check(nativeStatus(engine).getJSONArray("turns").length()==0,"Acknowledged utterance removed");
            call("nativePause",new Class[]{long.class,boolean.class},engine,true);int before=nativeStatus(engine).getInt("seconds");
            call("nativeFeed",new Class[]{long.class,short[].class,int.class},engine,audio,1600);check(nativeStatus(engine).getInt("seconds")==before,"Paused engine rejects captured audio");
        }finally{call("nativeDestroy",new Class[]{long.class},engine);}
        MainActivity activity=(MainActivity)test.startActivitySync(new Intent(context,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK).putExtra("fred_demo",true));
        Field field=MainActivity.class.getDeclaredField("conversation");field.setAccessible(true);LocalConversation voice=null;long end=System.currentTimeMillis()+20000;
        while(voice==null&&System.currentTimeMillis()<end){voice=(LocalConversation)field.get(activity);Thread.sleep(100);}check(voice!=null,"Activity conversation controller");
        try{
            JSONObject started=new JSONObject(voice.action("{\"action\":\"start\",\"quality\":\"low\",\"execution\":\"pc\"}"));check(!started.has("error"),"Controller starts: "+started);String session=started.getString("session");until(voice,"listening",false);
            check(new JSONObject(voice.action(Json.object("action","stop","session","expired").toString())).has("error"),"Stale session rejected");
            MainActivity.AndroidBridge bridge=activity.new AndroidBridge();check(new JSONObject(bridge.voiceAction("{\"action\":\"start\"}")).has("error"),"Dictation cannot capture concurrently");
            voice.action(Json.object("action","mute","session",session,"muted",true).toString());JSONObject muted=until(voice,"listening",true);check(muted.getBoolean("muted"),"Mute waits for actual microphone closure");
            voice.action(Json.object("action","mute","session",session,"muted",false).toString());until(voice,"listening",false);
            voice.action(Json.object("action","playback","session",session,"playing",true,"interruptions",false).toString());until(voice,"listening",true);
            voice.action(Json.object("action","playback","session",session,"playing",false,"interruptions",false).toString());until(voice,"listening",false);
            voice.pause();until(voice,"stopped",true);result.put("microphone","AudioRecord opens; mute and playback close it; unmute resumes; background stops");
        }finally{voice.closeAndWait(10000);test.runOnMainSync(activity::finish);}
        ClientBackend backend=new ClientBackend(context,new SecureStore(context,"conversation-tests"),DemoTransport.profile(),true);
        try(LoopbackServer server=new LoopbackServer(context,backend)){
            check(backend.remote.check().optBoolean("connected"),"Demo connected");
            HttpURLConnection connection=(HttpURLConnection)new URL(server.origin()+"/v1/voice/speech").openConnection();connection.setRequestProperty("Authorization","Bearer "+backend.key);connection.setRequestProperty("Content-Type","application/json");connection.setRequestMethod("POST");connection.setDoOutput(true);connection.setReadTimeout(10000);
            byte[] body=Json.bytes(Json.object("request_id","fixture-speech","text","Bonjour.","stream",true));try(OutputStream out=connection.getOutputStream()){out.write(body);}
            check(connection.getResponseCode()==200,"Authenticated voice proxy");String received;try(InputStream input=connection.getInputStream()){received=new String(SecureStore.readBounded(input,65536),StandardCharsets.UTF_8);}finally{connection.disconnect();}
            check(received.contains("\"done\":true")&&received.contains("\"pcm\"")&&!received.contains("connection_error"),"Voice JSON terminal frame preserved without false stream failure");check(backend.remote.state().optBoolean("connected"),"Speech completion preserves model connection");
            backend.post("/client/preferences",Json.object("voice_quality","low","voice_execution","pc","voice_interruptions",false,"voice_volume",70,"voice_animation",true));
            result.put("loopback","Authenticated speech PCM and JSON done, preferences accepted, connection preserved");
        }
        return result.put("passed",true).toString();
    }
}
