package net.karenax.fred;

import android.app.*;
import android.content.*;
import android.os.*;
import org.json.*;
import java.io.*;
import java.lang.reflect.*;

final class VoiceChecks {
    private static android.view.accessibility.AccessibilityNodeInfo denyButton(android.view.accessibility.AccessibilityNodeInfo node){if(node==null)return null;String id=node.getViewIdResourceName();if(id!=null&&id.endsWith("/permission_deny_button"))return node;for(int i=0;i<node.getChildCount();i++){android.view.accessibility.AccessibilityNodeInfo found=denyButton(node.getChild(i));if(found!=null)return found;}return null;}
    private static Method method(String name,Class<?>...types)throws Exception{Method value=LocalVoice.class.getDeclaredMethod(name,types);value.setAccessible(true);return value;}
    private static JSONObject status(long engine)throws Exception{return new JSONObject((String)method("nativeStatus",long.class).invoke(null,engine));}
    private static JSONObject until(long engine,String phase)throws Exception{long end=System.currentTimeMillis()+600000;while(System.currentTimeMillis()<end){JSONObject value=status(engine);if(value.optString("phase").equals(phase))return value;if(value.optString("phase").equals("error"))throw new AssertionError(value.toString());Thread.sleep(50);}throw new AssertionError("Voice timeout "+status(engine));}
    static String run(Instrumentation test,Bundle args)throws Exception{
        System.loadLibrary("fredvoice");File folder=new File(test.getTargetContext().getFilesDir(),"voice");File model=new File(folder,"ggml-small.bin"),wave=new File(folder,"francais.wav");
        long started=System.currentTimeMillis(),engine=(Long)method("nativeCreate",String.class,String.class).invoke(null,model.getAbsolutePath(),test.getTargetContext().getApplicationInfo().nativeLibraryDir);JSONObject result=new JSONObject();
        try{
            until(engine,"listening");result.put("loading_ms",System.currentTimeMillis()-started);result.put("loaded_pss_kb",Debug.getPss());
            byte[] file;try(InputStream input=new FileInputStream(wave)){file=SecureStore.readBounded(input,4*1024*1024);}int offset=12,length=0,start=0;
            while(offset+8<=file.length){String tag=new String(file,offset,4,"US-ASCII");int size=(file[offset+4]&255)|((file[offset+5]&255)<<8)|((file[offset+6]&255)<<16)|((file[offset+7]&255)<<24);if(tag.equals("data")){start=offset+8;length=size;break;}offset+=8+size+(size&1);}
            if(length<=0||start+length>file.length)throw new AssertionError("WAV fixture invalid");short[] audio=new short[1600];boolean progressive=false;
            for(offset=start;offset<start+length;offset+=3200){int count=Math.min(1600,(start+length-offset)/2);for(int i=0;i<count;i++)audio[i]=(short)((file[offset+2*i]&255)|(file[offset+2*i+1]<<8));method("nativeFeed",long.class,short[].class,int.class).invoke(null,engine,audio,count);Thread.sleep(100);if(!status(engine).optString("text").isEmpty())progressive=true;}
            java.util.Arrays.fill(audio,(short)0);for(int i=0;i<18;i++){method("nativeFeed",long.class,short[].class,int.class).invoke(null,engine,audio,1600);Thread.sleep(100);}
            if(!status(engine).getString("phase").equals("listening"))throw new AssertionError("Silence ended dictation");
            method("nativeStop",long.class).invoke(null,engine);JSONObject done=until(engine,"ready");String text=done.getString("text").toLowerCase(java.util.Locale.ROOT);if(!text.contains("réunion")||!text.contains("demain"))throw new AssertionError("French transcription "+done);result.put("native_final",done).put("progressive",progressive).put("audio_seconds",length/32000.0);
        }finally{method("nativeDestroy",long.class).invoke(null,engine);}
        engine=(Long)method("nativeCreate",String.class,String.class).invoke(null,model.getAbsolutePath(),test.getTargetContext().getApplicationInfo().nativeLibraryDir);try{method("nativeCancel",long.class).invoke(null,engine);JSONObject cancelled=until(engine,"cancelled");if(!cancelled.getString("text").isEmpty())throw new AssertionError("Cancelled text retained");}finally{method("nativeDestroy",long.class).invoke(null,engine);}
        // Exercise the real Activity controller and actual AudioRecord permission.
        MainActivity activity=(MainActivity)test.startActivitySync(new Intent(test.getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK).putExtra("fred_demo",true));
        Field field=MainActivity.class.getDeclaredField("voice");field.setAccessible(true);LocalVoice voice=(LocalVoice)field.get(activity);JSONObject first=new JSONObject(voice.action("{\"action\":\"start\"}"));String session=first.getString("session");
        if(new JSONObject(voice.action("{\"action\":\"stop\",\"session\":\"stale\"}")).optString("error").isEmpty())throw new AssertionError("Stale command accepted");
        boolean granted=activity.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==android.content.pm.PackageManager.PERMISSION_GRANTED;
        if(granted){long end=System.currentTimeMillis()+30000;while(!new JSONObject(voice.status()).optString("phase").equals("listening")&&System.currentTimeMillis()<end)Thread.sleep(100);if(!new JSONObject(voice.status()).optString("phase").equals("listening"))throw new AssertionError("AudioRecord start failed "+voice.status());Thread.sleep(500);voice.pause();end=System.currentTimeMillis()+30000;while(!new JSONObject(voice.status()).optString("phase").equals("ready")&&System.currentTimeMillis()<end)Thread.sleep(100);if(!new JSONObject(voice.status()).optString("phase").equals("ready"))throw new AssertionError("Background microphone stop failed "+voice.status());result.put("microphone","AudioRecord opened, background pause closed it, final text retained");}
        else{if(!first.optString("phase").equals("permission"))throw new AssertionError("Permission gate missing");android.accessibilityservice.AccessibilityServiceInfo info=test.getUiAutomation().getServiceInfo();info.flags|=android.accessibilityservice.AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;test.getUiAutomation().setServiceInfo(info);long end=System.currentTimeMillis()+20000;android.view.accessibility.AccessibilityNodeInfo deny=null;while(deny==null&&System.currentTimeMillis()<end){deny=denyButton(test.getUiAutomation().getRootInActiveWindow());Thread.sleep(100);}if(deny==null||!deny.performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK))throw new AssertionError("Real microphone permission dialog missing");while(!new JSONObject(voice.status()).optString("phase").equals("error")&&System.currentTimeMillis()<end)Thread.sleep(100);if(!new JSONObject(voice.status()).optString("phase").equals("error"))throw new AssertionError("Denial not reported");result.put("microphone","Real Android permission dialog denied safely; no capture opened");}
        voice.close();test.runOnMainSync(activity::finish);result.put("released_pss_kb",Debug.getPss()).put("passed",true);return result.toString();
    }
}
