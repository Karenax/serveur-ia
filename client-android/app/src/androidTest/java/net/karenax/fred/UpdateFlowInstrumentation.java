package net.karenax.fred;

import android.app.Instrumentation;
import android.content.*;
import android.os.Bundle;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** Explicit isolated fixture only. Downloads a future signed APK; leaves final confirmation to Android. */
public final class UpdateFlowInstrumentation extends Instrumentation {
    private Bundle arguments;
    @Override public void onCreate(Bundle arguments){super.onCreate(arguments);this.arguments=arguments;start();}
    @Override public void onStart(){Bundle result=new Bundle();
        try{
            if(arguments==null||!arguments.containsKey("fred_update_fixture"))throw new AssertionError("Explicit fixture required");
            JSONObject profile=Profile.validate(new JSONObject(new String(android.util.Base64.decode(arguments.getString("fred_update_fixture"),android.util.Base64.DEFAULT),StandardCharsets.UTF_8)));
            if(!"Fixture mises à jour Android".equals(Profile.name(profile))||!profile.getJSONObject("wireguard").getString("endpoint").startsWith("10.0.2.2:"))throw new AssertionError("Isolated emulator fixture required");
            Context context=getTargetContext();SecureStore store=new SecureStore(context,"update-test-vault");
            try(Remote remote=new Remote(context,profile,Json.object("endpoint",profile.getJSONObject("wireguard").getString("endpoint"),"connection_selected",true),false,store);
                    AndroidUpdates updates=new AndroidUpdates(context,remote,false)){
                JSONObject manifest=remote.json("/v1/client/android/release",null);
                AndroidUpdates.validateManifest(manifest);
                File previous=new File(new File(context.getFilesDir(),"updates"),manifest.getString("sha256")+".apk");
                previous.delete(); // Only this explicitly isolated future fixture, never an installed APK.
                updates.schedule(true);long deadline=System.currentTimeMillis()+60000;
                while(!"ready".equals(updates.state().optString("phase"))){
                    if("error".equals(updates.state().optString("phase"))||System.currentTimeMillis()>deadline)throw new AssertionError("Native update download failed");
                    Thread.sleep(100);
                }
                File apk=updates.installationFile();
                Intent intent=AndroidUpdates.installIntent(context,apk);
                long count=0;
                try(InputStream input=context.getContentResolver().openInputStream(intent.getData())){
                    byte[] buffer=new byte[65536];int n;while((n=input.read(buffer))!=-1)count+=n;
                }
                if(count!=apk.length())throw new AssertionError("Provider content incomplete");
                boolean refused=false;
                try{context.getContentResolver().openFileDescriptor(intent.getData(),"w");}catch(FileNotFoundException expected){refused=true;}
                if(!refused)throw new AssertionError("Provider allowed writing");
                if(!context.getPackageManager().canRequestPackageInstalls())throw new AssertionError("Installer permission required in fixture");
                context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                // Finishing instrumentation kills its host and URI grants. Keep it alive
                // until the Android installer has copied the APK, as the real activity does.
                Thread.sleep(6000);
                result.putString("stream","PASS automatic native WireGuard download, signed newer APK validation, read-only URI provider and Android installer launch ("+count+" bytes)\n");
            }
            finish(-1,result);
        }catch(Throwable error){result.putString("stream","FAIL "+error.getClass().getSimpleName()+": "+error.getMessage());finish(1,result);}
    }
}
