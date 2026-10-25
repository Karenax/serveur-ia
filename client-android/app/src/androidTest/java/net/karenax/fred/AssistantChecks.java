package net.karenax.fred;

import android.app.Instrumentation;
import android.app.job.*;
import android.content.Context;
import android.net.Uri;
import com.k2fsa.sherpa.onnx.*;
import java.io.*;
import java.nio.*;

/** Real JNI and Android scheduling on fictional data; no microphone or account. */
final class AssistantChecks {
    static String run(Instrumentation test)throws Exception {
        Context target=test.getTargetContext();StringBuilder log=new StringBuilder();
        OnlineTransducerModelConfig transducer=new OnlineTransducerModelConfig();
        transducer.setEncoder("wakeword/encoder.onnx");transducer.setDecoder("wakeword/decoder.onnx");transducer.setJoiner("wakeword/joiner.onnx");
        OnlineModelConfig model=new OnlineModelConfig();model.setTransducer(transducer);model.setTokens("wakeword/tokens.txt");model.setNumThreads(1);model.setProvider("cpu");
        KeywordSpotterConfig config=new KeywordSpotterConfig();config.setModelConfig(model);config.setKeywordsFile("wakeword/keywords.txt");config.setKeywordsScore(1.5f);config.setKeywordsThreshold(.25f);
        KeywordSpotter spotter=new KeywordSpotter(target.getAssets(),config);
        try{
            for(String name:new String[]{"bonjour-kiara","clara","ordinary"}){
                float[] samples=wav(test,name);OnlineStream stream=spotter.createStream("");int detections=0;
                try{
                    for(int at=0;at<samples.length;at+=1600){float[] chunk=java.util.Arrays.copyOfRange(samples,at,Math.min(at+1600,samples.length));stream.acceptWaveform(chunk,16000);while(spotter.isReady(stream)){spotter.decode(stream);if(!spotter.getResult(stream).getKeyword().isEmpty()){detections++;spotter.reset(stream);}}}
                }finally{stream.release();}
                check(name.equals("bonjour-kiara")?detections>0:detections==0,"Native keyword result: "+name+" = "+detections);
                log.append("PASS JNI keyword spotter: ").append(name).append(" = ").append(detections).append('\n');
            }
        }finally{spotter.release();}
        Uri photo=PhotoProvider.create(target);
        try{try(OutputStream out=target.getContentResolver().openOutputStream(photo,"w")){check(out!=null,"Photo output");out.write(new byte[]{1,2,3});}check(PhotoProvider.file(target,photo).length()==3,"Scoped temporary photo output");
            try{PhotoProvider.file(target,Uri.parse("content://"+target.getPackageName()+".photos/../../profile"));throw new AssertionError("Path escape accepted");}catch(FileNotFoundException expected){}
        }finally{PhotoProvider.file(target,photo).delete();}
        log.append("PASS photo provider output and path isolation\n");
        JobScheduler scheduler=target.getSystemService(JobScheduler.class);JobInfo previous=scheduler.getPendingJob(BackgroundNotifications.JOB);
        try{BackgroundNotifications.setEnabled(target,"assistant-check",true);JobInfo job=scheduler.getPendingJob(BackgroundNotifications.JOB);check(job!=null&&job.isPersisted()&&job.isPeriodic()&&job.getIntervalMillis()>=15*60*1000,"Android periodic inbox job");}
        finally{BackgroundNotifications.setEnabled(target,"assistant-check",false);new SecureStore(target).delete("assistant-check.background-alerts");if(previous!=null)scheduler.schedule(previous);}
        log.append("PASS optional Android scheduler registered and cancelled\n");
        log.append("LIMIT synthetic speech and emulator; no human microphone, camera app, battery or guaranteed background delay\n");
        return log.toString();
    }
    private static float[] wav(Instrumentation test,String name)throws Exception {
        byte[] raw;try(InputStream source=test.getContext().getAssets().open("assistant/"+name+".wav")){raw=SecureStore.readBounded(source,2*1024*1024);}
        ByteBuffer bytes=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);int rate=bytes.getInt(24),position=12,start=-1,count=0;
        while(position+8<=raw.length){int size=bytes.getInt(position+4);if(size<0||position+8L+size>raw.length)throw new IOException();String kind=new String(raw,position,4,java.nio.charset.StandardCharsets.US_ASCII);if(kind.equals("data")){start=position+8;count=size/2;break;}position+=8+size+(size%2);}
        check(start>=0&&rate>0,"Synthetic WAV");int length=(int)((long)count*16000/rate);float[] result=new float[length+16000];
        for(int i=0;i<length;i++){double at=(double)i*rate/16000;int first=(int)at,last=Math.min(first+1,count-1);result[i]=(float)((bytes.getShort(start+first*2)*(1-(at-first))+bytes.getShort(start+last*2)*(at-first))/32768);}
        return result;
    }
    private static void check(boolean passed,String message){if(!passed)throw new AssertionError(message);}
}
