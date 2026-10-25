package net.karenax.fred;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.*;
import com.k2fsa.sherpa.onnx.*;
import org.json.*;
import java.io.InputStream;
import java.security.MessageDigest;

/** Foreground-only, local keyword spotting. Audio is neither stored nor sent. */
final class WakeWord implements AutoCloseable {
    static final int PERMISSION=907;
    private final Activity activity;
    private volatile boolean stopped=true;
    private volatile Thread worker;
    private volatile AudioRecord microphone;
    private String phase="stopped",message="",session="";
    WakeWord(Activity activity){this.activity=activity;}
    synchronized String status(){return Json.object("phase",phase,"message",message,"session",session,"installed",true,"experimental",true,"microphone_closed",microphone==null).toString();}
    String action(String body){
        try{
            JSONObject value=new JSONObject(body);String action=value.optString("action");
            if(action.equals("stop")){if(!stopAndWait())throw new IllegalStateException("Le microphone se ferme encore. Réessayez.");return status();}
            synchronized(this){
            if(!action.equals("start"))throw new IllegalArgumentException("Commande d’activation inconnue.");
            if(worker!=null&&worker.isAlive())throw new IllegalStateException("Le mot d’appel est déjà actif.");
            session=Json.token();message="";
            if(activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){phase="permission";activity.runOnUiThread(()->activity.requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},PERMISSION));return status();}
            start();return status();
            }
        }catch(Exception e){return Json.object("error",Remote.safeMessage(e)).toString();}
    }
    synchronized void permission(boolean granted){if(!phase.equals("permission"))return;if(!granted){phase="error";message="Microphone refusé. Vous pouvez démarrer le vocal avec le bouton.";return;}start();}
    private void start(){stopped=false;phase="loading";worker=new Thread(this::record,"kiara-wakeword");worker.start();}
    private void verify()throws Exception {
        JSONObject manifest;
        try(InputStream source=activity.getAssets().open("wakeword/manifest.json")){manifest=new JSONObject(new String(SecureStore.readBounded(source,65536),java.nio.charset.StandardCharsets.UTF_8));}
        JSONArray files=manifest.getJSONArray("files");
        for(int i=0;i<files.length();i++){
            JSONObject entry=files.getJSONObject(i);String name=entry.getString("name");
            if(!name.matches("[a-z.-]+"))throw new java.io.IOException();
            try(InputStream source=activity.getAssets().open("wakeword/"+name)){
                MessageDigest hash=MessageDigest.getInstance("SHA-256");byte[] buffer=new byte[16384];int count,total=0;
                while((count=source.read(buffer))!=-1){total+=count;if(total>entry.getInt("bytes"))throw new java.io.IOException();hash.update(buffer,0,count);}
                StringBuilder hex=new StringBuilder();for(byte b:hash.digest())hex.append(String.format(java.util.Locale.ROOT,"%02x",b&255));
                if(total!=entry.getInt("bytes")||!hex.toString().equals(entry.getString("sha256")))throw new java.io.IOException();
            }
        }
    }
    private void record(){KeywordSpotter spotter=null;OnlineStream stream=null;AudioRecord record=null;
        try{
            verify();OnlineTransducerModelConfig transducer=new OnlineTransducerModelConfig();
            transducer.setEncoder("wakeword/encoder.onnx");transducer.setDecoder("wakeword/decoder.onnx");transducer.setJoiner("wakeword/joiner.onnx");
            OnlineModelConfig model=new OnlineModelConfig();model.setTransducer(transducer);model.setTokens("wakeword/tokens.txt");model.setNumThreads(1);model.setProvider("cpu");
            KeywordSpotterConfig config=new KeywordSpotterConfig();config.setModelConfig(model);config.setKeywordsFile("wakeword/keywords.txt");config.setKeywordsScore(1.5f);config.setKeywordsThreshold(.4f);
            spotter=new KeywordSpotter(activity.getAssets(),config);stream=spotter.createStream("");
            if(stopped)return;
            int min=AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
            if(activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)throw new SecurityException("Microphone non autorisé.");
            record=new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(min,6400));
            if(record.getState()!=AudioRecord.STATE_INITIALIZED)throw new java.io.IOException();
            microphone=record;record.startRecording();synchronized(this){if(!stopped)phase="listening";}
            short[] pcm=new short[1600];AudioManager manager=(AudioManager)activity.getSystemService(Context.AUDIO_SERVICE);
            while(!stopped){
                if(manager.getMode()!=AudioManager.MODE_NORMAL)throw new IllegalStateException("Activation interrompue par un appel audio.");
                int count=record.read(pcm,0,pcm.length,AudioRecord.READ_BLOCKING);if(count<=0){if(stopped)break;throw new java.io.IOException();}
                float[] samples=new float[count];for(int i=0;i<count;i++)samples[i]=pcm[i]/32768f;
                stream.acceptWaveform(samples,16000);
                while(!stopped&&spotter.isReady(stream)){
                    spotter.decode(stream);
                    if(!spotter.getResult(stream).getKeyword().isEmpty()){synchronized(this){phase="detected";}stopped=true;break;}
                }
            }
        }catch(Throwable e){synchronized(this){if(!stopped){phase="error";message="Activation vocale indisponible. Démarrez avec le bouton.";}}}
        finally{
            if(record!=null){try{record.stop();}catch(Exception ignored){}record.release();}microphone=null;
            if(stream!=null)stream.release();if(spotter!=null)spotter.release();
            synchronized(this){if(!phase.equals("detected")&&!phase.equals("error"))phase="stopped";}
        }
    }
    boolean stopAndWait(){stopped=true;AudioRecord record=microphone;if(record!=null)try{record.stop();}catch(Exception ignored){}
        Thread current=worker;if(current!=null&&current!=Thread.currentThread())try{current.join(3000);}catch(InterruptedException e){Thread.currentThread().interrupt();}
        boolean closed=current==null||!current.isAlive();if(closed)synchronized(this){phase="stopped";}return closed;
    }
    @Override public void close(){stopAndWait();}
}
