package net.karenax.fred;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.media.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.UUID;

/** Local PCM only: no recording file, no request to Fred, no cloud fallback. */
final class LocalVoice implements AutoCloseable {
    static final int PERMISSION=45;
    private final Activity activity;
    private final JSONObject spec;
    private final File model,partial;
    private final Object lock=new Object();
    private JSONObject value=Json.object("phase","idle","text","","session","","seconds",0,"message","Dictée locale · français");
    private Thread worker;
    private long handle;
    private volatile boolean cancelled,closed;
    private boolean permissionPending;
    private long verifiedTime=-1;
    private static native long nativeCreate(String path,String backends);
    private static native void nativeFeed(long handle,short[] audio,int count);
    private static native String nativeStatus(long handle);
    private static native void nativeStop(long handle);
    private static native void nativeCancel(long handle);
    private static native void nativeDestroy(long handle);

    LocalVoice(Activity activity) throws Exception {
        this.activity=activity;
        try(InputStream input=activity.getAssets().open("voice/model.json")) {spec=new JSONObject(new String(SecureStore.readBounded(input,16384),StandardCharsets.UTF_8));}
        File folder=new File(activity.getFilesDir(),"voice");model=new File(folder,"ggml-small.bin");partial=new File(folder,"ggml-small.part");
    }
    private boolean installed(){return model.isFile()&&model.length()==spec.optLong("bytes");}
    private String phase(){return value.optString("phase");}
    private static boolean active(String phase){return java.util.Arrays.asList("installing","verifying","permission","loading","listening","finishing","cancelling").contains(phase);}
    String status(){synchronized(lock){try{if(handle!=0&&!phase().equals("error"))merge(new JSONObject(nativeStatus(handle)));return new JSONObject(value.toString()).put("installed",installed()).put("model","Whisper Small").put("model_bytes",spec.getLong("bytes")).put("local",true).toString();}catch(Exception e){return Json.object("phase","error","message","État vocal indisponible.").toString();}}}
    private void merge(JSONObject update)throws JSONException{for(java.util.Iterator<String> keys=update.keys();keys.hasNext();){String key=keys.next();value.put(key,update.get(key));}}
    private void state(String phase,String message){try{value.put("phase",phase).put("message",message);}catch(JSONException impossible){throw new IllegalStateException(impossible);}}
    String action(String raw){synchronized(lock){try{
        if(raw==null||raw.length()>1024||closed)throw new IllegalArgumentException("Commande vocale indisponible.");
        JSONObject command=new JSONObject(raw);for(java.util.Iterator<String> keys=command.keys();keys.hasNext();)if(!java.util.Arrays.asList("action","session").contains(keys.next()))throw new IllegalArgumentException("Commande vocale invalide.");
        String action=command.getString("action");status();
        if(action.equals("stop")||action.equals("cancel")){
            if(command.optString("session").isEmpty()||!command.optString("session").equals(value.optString("session")))throw new IllegalArgumentException("Cette dictée n’est plus active.");
            if(handle!=0){if(action.equals("stop"))nativeStop(handle);else nativeCancel(handle);}
            else if(active(phase())){cancelled=true;permissionPending=false;state("cancelling","Arrêt de la dictée…");if(worker==null||!worker.isAlive())state("cancelled","Dictée annulée.");}
            else if(action.equals("cancel")){value.put("text","");state("cancelled","Dictée annulée.");}
            return status();
        }
        if(!java.util.Arrays.asList("start","install","remove").contains(action))throw new IllegalArgumentException("Commande vocale invalide.");
        if(active(phase())||(worker!=null&&worker.isAlive()))throw new IllegalArgumentException("Une opération vocale est déjà en cours.");
        if(action.equals("remove")){Files.deleteIfExists(model.toPath());Files.deleteIfExists(partial.toPath());verifiedTime=-1;state("idle","Dictée désinstallée.");return status();}
        if(action.equals("start")&&!installed())throw new IllegalArgumentException("Installez la dictée française avant d’ouvrir le microphone.");
        cancelled=false;value=Json.object("phase",action.equals("install")?"installing":"loading","text","","seconds",0,"session",UUID.randomUUID().toString(),"message",action.equals("install")?"Installation de la dictée…":"Chargement de la dictée…");
        if(action.equals("install"))launch(this::install);
        else if(activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){permissionPending=true;state("permission","Autorisez le microphone pour dicter.");String session=value.getString("session");activity.runOnUiThread(()->{synchronized(lock){if(permissionPending&&!closed&&session.equals(value.optString("session")))activity.requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},PERMISSION);}});}
        else launch(this::record);
        return status();
    }catch(Exception e){return Json.object("error",e instanceof IllegalArgumentException?e.getMessage():"Commande vocale invalide ou indisponible.").toString();}}}
    private void launch(Runnable job){worker=new Thread(job,"Fred-local-voice");worker.start();}
    void permissionResult(boolean granted){synchronized(lock){if(!permissionPending||closed||cancelled)return;permissionPending=false;if(granted){state("loading","Chargement de la dictée…");launch(this::record);}else state("error","Microphone refusé. Autorisez-le dans les paramètres Android puis réessayez.");}}
    void pause(){synchronized(lock){if(permissionPending)return;if(handle!=0)nativeStop(handle);else if(active(phase())){cancelled=true;state("cancelling","Arrêt de la dictée…");}}}
    private void verify()throws Exception{
        if(installed()&&verifiedTime==model.lastModified())return;
        if(!installed()||!digest(model).equals(spec.getString("sha256")))throw new IllegalArgumentException("Fichier de dictée invalide. Réinstallez la dictée française.");
        verifiedTime=model.lastModified();
    }
    private static String digest(File file)throws Exception{MessageDigest hash=MessageDigest.getInstance("SHA-256");try(InputStream input=new FileInputStream(file)){byte[] buffer=new byte[262144];int count;while((count=input.read(buffer))!=-1)hash.update(buffer,0,count);}StringBuilder text=new StringBuilder();for(byte b:hash.digest())text.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return text.toString();}
    private void install(){try{
        if(!model.getParentFile().isDirectory()&&!model.getParentFile().mkdirs())throw new IOException();
        if(installed()){try{verify();return;}catch(IllegalArgumentException corrupt){/* A verified replacement may repair corruption. */}}
        long expected=spec.getLong("bytes"),offset=partial.isFile()?partial.length():0;if(offset>=expected)offset=0;
        if(model.getParentFile().getUsableSpace()<expected-offset+64L*1024*1024)throw new IllegalArgumentException("Il faut environ 550 Mo d’espace libre pour installer la dictée.");
        URL url=new URL(spec.getString("url"));HttpURLConnection connection=null;
        try{
            for(int redirects=0;redirects<6;redirects++){
                if(cancelled)return;if(!url.getProtocol().equals("https"))throw new IOException();
                connection=(HttpURLConnection)url.openConnection();connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(20000);connection.setReadTimeout(20000);connection.setRequestProperty("User-Agent","Fred-local-dictation/1.0");if(offset>0)connection.setRequestProperty("Range","bytes="+offset+"-");
                int code=connection.getResponseCode();if(code>=300&&code<400){String location=connection.getHeaderField("Location");if(location==null)throw new IOException();URL next=new URL(url,location);connection.disconnect();url=next;continue;}
                if(code==200)offset=0;else if(code!=206||!String.valueOf(connection.getHeaderField("Content-Range")).startsWith("bytes "+offset+"-"))throw new IOException();
                long size=offset;try(InputStream input=connection.getInputStream();OutputStream output=new FileOutputStream(partial,offset>0)){byte[] buffer=new byte[262144];int count;while(!cancelled&&(count=input.read(buffer))!=-1){size+=count;if(size>expected)throw new IOException();output.write(buffer,0,count);synchronized(lock){value.put("downloaded_bytes",size);}}}
                if(cancelled)return;synchronized(lock){state("verifying","Vérification de la dictée…");}
                if(size!=expected||!digest(partial).equals(spec.getString("sha256"))){Files.deleteIfExists(partial.toPath());throw new IllegalArgumentException("Téléchargement incomplet ou invalide. Réessayez.");}
                if(cancelled)return;Files.move(partial.toPath(),model.toPath(),StandardCopyOption.REPLACE_EXISTING);verifiedTime=model.lastModified();return;
            }throw new IOException();
        }finally{if(connection!=null)connection.disconnect();}
    }catch(Exception e){synchronized(lock){state("error",e instanceof IllegalArgumentException?e.getMessage():"Installation impossible. Vérifiez Internet et l’espace disponible.");}}
    finally{synchronized(lock){if(!phase().equals("error"))state(cancelled?"cancelled":"idle",cancelled?"Installation annulée.":"Dictée installée. Vous pouvez ouvrir le microphone.");}}}
    private void record(){long engine=0;AudioRecord microphone=null;try{
        verify();if(cancelled)return;System.loadLibrary("fredvoice");
        synchronized(lock){if(cancelled||closed)return;engine=nativeCreate(model.getAbsolutePath(),activity.getApplicationInfo().nativeLibraryDir);if(engine==0)throw new IOException();handle=engine;}
        short[] audio=new short[1600];
        while(true){String phase;synchronized(lock){merge(new JSONObject(nativeStatus(engine)));phase=phase();}
            if(phase.equals("listening")){
                if(microphone==null){int minimum=AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);if(minimum<0)throw new IOException();microphone=new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(minimum,12800));if(microphone.getState()!=AudioRecord.STATE_INITIALIZED)throw new IOException();microphone.startRecording();if(microphone.getRecordingState()!=AudioRecord.RECORDSTATE_RECORDING)throw new IOException();}
                int count=microphone.read(audio,0,audio.length,AudioRecord.READ_BLOCKING);if(count<0)throw new IOException();if(count>0)synchronized(lock){nativeFeed(engine,audio,count);}
            }else{
                if(microphone!=null){microphone.stop();microphone.release();microphone=null;}
                if(java.util.Arrays.asList("ready","cancelled","error").contains(phase))break;
                Thread.sleep(50);
            }
        }
    }catch(Exception|LinkageError e){synchronized(lock){if(engine!=0)nativeCancel(engine);state("error",e instanceof IllegalArgumentException?e.getMessage():"Dictée indisponible. Vérifiez le microphone et réessayez.");}}
    finally{if(microphone!=null){try{microphone.stop();}catch(Exception ignored){}microphone.release();}synchronized(lock){handle=0;}if(engine!=0)nativeDestroy(engine);synchronized(lock){if(cancelled&&!phase().equals("error")){try{value.put("text","");}catch(JSONException ignored){}state("cancelled","Dictée annulée.");}}}}
    @Override public void close(){synchronized(lock){closed=true;cancelled=true;permissionPending=false;if(handle!=0)nativeCancel(handle);}}
}
