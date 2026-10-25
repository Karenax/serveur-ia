package net.karenax.fred;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.media.*;
import android.media.audiofx.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Continuous Low conversation. Audio stays in memory; only final text reaches Kiara. */
final class LocalConversation implements AutoCloseable {
    static final int PERMISSION=46;
    private final Activity activity;
    private final LocalVoice dictation;
    private final Object control,lock=new Object();
    private JSONObject value=Json.object("phase","idle","session","","partial","","turns",new JSONArray());
    private Thread worker;
    private long handle;
    private volatile boolean stopped,closed;
    private boolean muted,confirmedMuted,microphoneClosed=true,playing,interruptions,permissionPending,foreground=true;
    private String installSession="";
    private int acknowledged;
    private static native long nativeCreate(String model,String backends);
    private static native void nativeFeed(long engine,short[] audio,int count);
    private static native String nativeStatus(long engine);
    private static native void nativePause(long engine,boolean paused);
    private static native void nativeAck(long engine,int turn);
    private static native void nativeCancel(long engine);
    private static native void nativeDestroy(long engine);

    LocalConversation(Activity activity,LocalVoice dictation,Object control){this.activity=activity;this.dictation=dictation;this.control=control;}
    private String phase(){return value.optString("phase");}
    private void state(String phase,String message){try{value.put("phase",phase).put("message",message);}catch(JSONException impossible){throw new IllegalStateException(impossible);}}
    boolean busy(){synchronized(lock){return permissionPending||worker!=null&&worker.isAlive()||!installSession.isEmpty()||Arrays.asList("loading","permission","listening","stopping").contains(phase());}}
    private void merge(JSONObject next)throws JSONException{for(Iterator<String> keys=next.keys();keys.hasNext();){String key=keys.next();if(!key.equals("phase")&&!key.equals("message"))value.put(key,next.get(key));}}
    String status(){synchronized(lock){try{
        if(!installSession.isEmpty()){
            JSONObject install=new JSONObject(dictation.status());
            if(!installSession.equals(install.optString("session"))){installSession="";state("error","Installation interrompue. Réessayez.");}
            else if(Arrays.asList("installing","verifying","cancelling").contains(install.optString("phase"))){state("installing",install.optString("message"));value.put("downloaded_bytes",install.optLong("downloaded_bytes"));}
            else{installSession="";state(install.optString("phase").equals("error")?"error":"idle",install.optString("message"));}
        }
        if(handle!=0){JSONObject nativeValue=new JSONObject(nativeStatus(handle));merge(nativeValue);if(nativeValue.optString("phase").equals("error"))state("error",nativeValue.optString("message"));}
        if(stopped&&worker!=null&&worker.isAlive())state("stopping","Fermeture du microphone…");
        return new JSONObject(value.toString()).put("installed",dictation.modelInstalled()).put("model_bytes",dictation.modelBytes())
            .put("model","Whisper Small").put("quality","low").put("execution","pc").put("local",true)
            .put("muted",confirmedMuted).put("mute_pending",muted!=confirmedMuted).put("microphone_closed",microphoneClosed)
            .put("playback_paused",playing&&!interruptions).put("aec_supported",AcousticEchoCanceler.isAvailable()).toString();
    }catch(Exception e){return Json.object("phase","error","message","État du vocal indisponible.","microphone_closed",microphoneClosed).toString();}}}

    String action(String raw){synchronized(control){synchronized(lock){try{
        if(closed||raw==null||raw.length()>2048)throw new IllegalArgumentException("Conversation indisponible.");
        JSONObject command=new JSONObject(raw);String action=command.getString("action");status();
        if(action.equals("start")||action.equals("install")){
            Json.keys(command,"action","quality","execution");
            if(!command.optString("quality","low").equals("low")||!command.optString("execution","pc").equals("pc"))throw new IllegalArgumentException("Choisissez le mode Low sur cet appareil.");
            if(busy()||dictation.busy())throw new IllegalArgumentException("Terminez la dictée ou le vocal avant de démarrer.");
            stopped=false;muted=confirmedMuted=playing=interruptions=false;acknowledged=0;microphoneClosed=true;
            value=Json.object("phase","loading","session",UUID.randomUUID().toString(),"partial","","turns",new JSONArray(),"speech_id",0);
            if(action.equals("install")){
                JSONObject installation=new JSONObject(dictation.action(Json.object("action","install").toString()));
                if(installation.has("error"))throw new IllegalArgumentException(installation.optString("error"));
                installSession=installation.getString("session");state("installing","Installation de la reconnaissance française…");return status();
            }
            if(!dictation.modelInstalled())throw new IllegalArgumentException("Installez la reconnaissance française avant de parler.");
            if(activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
                permissionPending=true;state("permission","Autorisez le microphone pour discuter avec Kiara.");String session=value.getString("session");
                activity.runOnUiThread(()->{synchronized(lock){if(permissionPending&&!closed&&!stopped&&session.equals(value.optString("session")))activity.requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},PERMISSION);}});
            }else launch();
            return status();
        }
        if(!command.optString("session").equals(value.optString("session"))||command.optString("session").isEmpty())throw new IllegalArgumentException("Cette conversation vocale est terminée.");
        if(action.equals("stop")){
            Json.keys(command,"action","session");stop();return status();
        }
        if(stopped||!Arrays.asList("permission","loading","listening").contains(phase()))throw new IllegalArgumentException("Le vocal est arrêté.");
        if(action.equals("mute")){
            Json.keys(command,"action","session","muted");muted=Json.bool(command,"muted",false);
            if(handle==0&&microphoneClosed)confirmedMuted=muted;
        }else if(action.equals("playback")){
            Json.keys(command,"action","session","playing","interruptions");playing=Json.bool(command,"playing",false);
            interruptions=Json.bool(command,"interruptions",false)&&AcousticEchoCanceler.isAvailable();
        }else if(action.equals("ack")){
            Json.keys(command,"action","session","turn");Object rawTurn=command.get("turn");
            if(!(rawTurn instanceof Integer||rawTurn instanceof Long)||((Number)rawTurn).longValue()<0||((Number)rawTurn).longValue()>Integer.MAX_VALUE)throw new IllegalArgumentException("Phrase vocale invalide.");
            int turn=((Number)rawTurn).intValue();JSONArray turns=value.optJSONArray("turns");int last=acknowledged;
            if(turns!=null)for(int i=0;i<turns.length();i++)last=Math.max(last,turns.getJSONObject(i).getInt("id"));
            if(turn>last)throw new IllegalArgumentException("Phrase vocale expirée.");if(handle!=0)nativeAck(handle,turn);acknowledged=Math.max(acknowledged,turn);
        }else throw new IllegalArgumentException("Commande vocale invalide.");
        if(handle!=0)nativePause(handle,muted||playing&&!interruptions);
        return status();
    }catch(Exception e){return Json.object("error",e instanceof IllegalArgumentException?e.getMessage():"Commande vocale invalide.").toString();}}}}

    private void launch(){state("loading","Chargement de la reconnaissance française…");worker=new Thread(this::record,"Kiara-low-conversation");worker.start();}
    void permissionResult(boolean granted){synchronized(lock){if(!permissionPending||closed||stopped)return;if(!granted){permissionPending=false;state("error","Microphone refusé. Autorisez-le dans les paramètres Android puis réessayez.");}else if(foreground){permissionPending=false;launch();}}}
    void resume(){synchronized(lock){foreground=true;if(permissionPending&&!closed&&!stopped&&activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED){permissionPending=false;launch();}}}
    void pause(){synchronized(lock){foreground=false;if(!permissionPending)stop();}}
    private void stop(){stopped=true;permissionPending=false;
        if(!installSession.isEmpty()){dictation.action(Json.object("action","cancel","session",installSession).toString());}
        if(handle!=0)nativeCancel(handle);
        state(worker!=null&&worker.isAlive()?"stopping":"stopped","Conversation terminée.");
    }
    boolean closeAndWait(long milliseconds)throws InterruptedException{close();Thread current;synchronized(lock){current=worker;}if(current!=null)current.join(milliseconds);return current==null||!current.isAlive();}
    @Override public void close(){synchronized(lock){closed=true;stop();}}

    private void record(){long engine=0;AudioRecord microphone=null;AcousticEchoCanceler echo=null;NoiseSuppressor noise=null;AudioManager manager=(AudioManager)activity.getSystemService(Activity.AUDIO_SERVICE);AudioFocusRequest focus=null;final String owner;synchronized(lock){owner=value.optString("session");}
        try{
            File model;try{model=dictation.verifiedModel();}catch(Exception e){throw new IllegalArgumentException("Modèle vocal corrompu. Réinstallez la reconnaissance française.");}
            if(stopped||closed)return;System.loadLibrary("fredvoice");
            synchronized(lock){if(stopped||closed)return;engine=nativeCreate(model.getAbsolutePath(),activity.getApplicationInfo().nativeLibraryDir);if(engine==0)throw new IOException();handle=engine;nativePause(engine,muted||playing&&!interruptions);}
            focus=new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT).setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()).setOnAudioFocusChangeListener(change->{if(change<0)synchronized(lock){if(owner.equals(value.optString("session")))stop();}}).build();
            if(manager.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED)throw new IllegalArgumentException("Le son est utilisé par une autre application. Réessayez après sa fermeture.");
            short[] audio=new short[1600];long deadline=android.os.SystemClock.elapsedRealtime()+15*60*1000L;
            while(!stopped&&!closed&&android.os.SystemClock.elapsedRealtime()<deadline){
                boolean capture;String phase; synchronized(lock){JSONObject current=new JSONObject(nativeStatus(engine));merge(current);phase=current.optString("phase");if(phase.equals("error"))throw new IllegalArgumentException(current.optString("message"));capture=!muted&&!(playing&&!interruptions)&&phase.equals("listening");}
                if(!capture){
                    if(microphone!=null){microphone.stop();microphone.release();microphone=null;}if(echo!=null){echo.release();echo=null;}if(noise!=null){noise.release();noise=null;}
                    synchronized(lock){microphoneClosed=true;confirmedMuted=muted;if(phase.equals("listening"))state("listening",muted?"Microphone coupé":"Kiara prépare sa réponse.");}
                    if(Arrays.asList("ready","cancelled").contains(phase))break;Thread.sleep(50);continue;
                }
                if(microphone==null){
                    if(activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)throw new IllegalArgumentException("Microphone refusé. Autorisez-le dans les paramètres Android.");
                    int size=AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);if(size<0)throw new IOException();
                    microphone=new AudioRecord(MediaRecorder.AudioSource.VOICE_COMMUNICATION,16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(size,12800));
                    if(microphone.getState()!=AudioRecord.STATE_INITIALIZED)throw new IOException();
                    if(AcousticEchoCanceler.isAvailable()){echo=AcousticEchoCanceler.create(microphone.getAudioSessionId());if(echo!=null)echo.setEnabled(true);}
                    if(NoiseSuppressor.isAvailable()){noise=NoiseSuppressor.create(microphone.getAudioSessionId());if(noise!=null)noise.setEnabled(true);}
                    microphone.startRecording();if(microphone.getRecordingState()!=AudioRecord.RECORDSTATE_RECORDING)throw new IOException();
                }
                synchronized(lock){microphoneClosed=false;confirmedMuted=false;state("listening","Kiara vous écoute.");}
                int count=microphone.read(audio,0,audio.length,AudioRecord.READ_BLOCKING);if(count<0)throw new IOException();
                if(count>0)synchronized(lock){if(!stopped&&!muted&&!(playing&&!interruptions)){nativeFeed(engine,audio,count);double sum=0;for(int i=0;i<count;i++)sum+=(double)audio[i]*audio[i];value.put("audio_level",Math.sqrt(sum/count)/32768);value.put("audio_level_at",System.currentTimeMillis()/1000.0);}}
            }
        }catch(Exception|LinkageError e){synchronized(lock){state("error",e instanceof IllegalArgumentException?e.getMessage():"Vocal indisponible. Vérifiez le microphone puis réessayez.");}}
        finally{
            if(microphone!=null){try{microphone.stop();}catch(Exception ignored){}microphone.release();}if(echo!=null)echo.release();if(noise!=null)noise.release();
            synchronized(lock){microphoneClosed=true;confirmedMuted=muted;handle=0;}
            if(engine!=0){nativeCancel(engine);nativeDestroy(engine);}if(focus!=null)manager.abandonAudioFocusRequest(focus);
            synchronized(lock){if(!phase().equals("error")){state("stopped","Conversation terminée.");try{value.put("turns",new JSONArray()).put("partial","");}catch(JSONException ignored){}}}
        }
    }
}
