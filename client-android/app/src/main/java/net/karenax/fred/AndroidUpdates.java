package net.karenax.fred;

import android.content.Context;
import android.content.Intent;
import android.content.ClipData;
import android.content.pm.*;
import android.net.Uri;
import android.os.Build;
import org.json.*;
import java.io.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;

/** Authenticated downloads; installation is always a separate Android confirmation. */
final class AndroidUpdates implements AutoCloseable {
    private static final long MAX_BYTES=128L*1024*1024;
    private final Context context;
    private final Remote remote;
    private final boolean demo;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private boolean working,closed;
    private long checkedAt;
    private JSONObject state=Json.object("phase","idle","message","Les mises à jour sont recherchées automatiquement.");
    private JSONObject readyRelease;
    private File readyFile;

    AndroidUpdates(Context context,Remote remote,boolean demo){this.context=context;this.remote=remote;this.demo=demo;}
    synchronized JSONObject state(){return Json.copy(state);}
    synchronized void schedule(boolean force){
        if(closed||working||demo||!remote.hasProfile()||remote.state().optBoolean("connection_required"))return;
        if(remote.active.get()>0)return;
        long now=System.currentTimeMillis();
        if(!force&&now-checkedAt<600000)return;
        checkedAt=now;working=true;
        worker.execute(()->{
            try{checkAndDownload();}
            catch(Exception error){setState("error","Mise à jour indisponible. Réessayez lorsque le serveur est accessible.",0,0);}
            finally{synchronized(this){working=false;}}
        });
    }
    private synchronized void setState(String phase,String message,long received,long total){
        if(closed)return;
        state=Json.object("phase",phase,"message",message,"received",received,"bytes",total,
                "version",readyRelease==null?"":readyRelease.optString("version"),"available",readyFile!=null);
    }
    private void checkAndDownload()throws Exception {
        setState("checking","Recherche d’une mise à jour Android…",0,0);
        JSONObject release=remote.json("/v1/client/android/release",null);
        validateManifest(release);
        long code=release.getLong("version_code");
        if(code<=BuildConfig.VERSION_CODE){
            synchronized(this){readyFile=null;readyRelease=null;}
            cleanCache(new File(context.getFilesDir(),"updates"),null);
            setState("current","Fred Android "+BuildConfig.VERSION_NAME+" est à jour.",0,0);return;
        }
        File directory=new File(context.getFilesDir(),"updates");
        if(!directory.isDirectory()&&!directory.mkdirs())throw new IOException();
        File target=new File(directory,release.getString("sha256")+".apk");
        if(target.isFile()){
            try{validateApk(context,target,release);markReady(target,release);return;}
            catch(Exception error){if(!target.delete())throw new IOException();}
        }
        File partial=new File(directory,"download-"+Json.token()+".part");
        Remote.Response response=null;
        remote.active.incrementAndGet();
        try{
            long total=release.getLong("bytes"),received=0;
            setState("downloading","Téléchargement de Fred Android "+release.getString("version")+"…",0,total);
            response=remote.open("/v1/client/android/download",null,null);
            if(response.status!=200)throw new IOException();
            try(FileOutputStream output=new FileOutputStream(partial)){
                byte[] buffer=new byte[65536];int count;
                while((count=response.input.read(buffer))!=-1){
                    if(Thread.currentThread().isInterrupted()||isClosed())throw new InterruptedIOException();
                    received+=count;if(received>total||received>MAX_BYTES)throw new IOException();
                    output.write(buffer,0,count);
                    setState("downloading","Téléchargement de Fred Android "+release.getString("version")+"…",received,total);
                }
                output.getFD().sync();
            }
            validateApk(context,partial,release);
            synchronized(this){if(closed)throw new InterruptedIOException();if(!partial.renameTo(target))throw new IOException();}
            markReady(target,release);
        }finally{
            partial.delete();if(response!=null)remote.finished(response);remote.active.decrementAndGet();
        }
    }
    private synchronized boolean isClosed(){return closed;}
    private synchronized void markReady(File file,JSONObject release){
        if(closed)return;readyRelease=Json.copy(release);readyFile=file;
        cleanCache(file.getParentFile(),file);
        setState("ready","Fred Android "+release.optString("version")+" est prêt à installer.",file.length(),file.length());
    }
    synchronized File installationFile()throws Exception {
        if(closed||working||readyFile==null||readyRelease==null)throw new IllegalArgumentException("Aucune mise à jour prête. Recherchez une mise à jour.");
        validateApk(context,readyFile,readyRelease);return readyFile;
    }
    static Intent installIntent(Context context,File apk){
        Uri uri=Uri.parse("content://"+context.getPackageName()+".updates/"+apk.getName());
        Intent intent=new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        intent.setClipData(ClipData.newRawUri("Mise à jour Fred",uri));return intent;
    }
    static void cleanCache(File directory,File retained){
        try{
            if(directory==null||!directory.isDirectory()||java.nio.file.Files.isSymbolicLink(directory.toPath()))return;
            File[] files=directory.listFiles();if(files==null)return;
            for(File file:files){
                if(!file.isFile()||!file.getCanonicalFile().getParentFile().equals(directory.getCanonicalFile()))continue;
                if(retained!=null&&file.getCanonicalFile().equals(retained.getCanonicalFile()))continue;
                if(file.getName().matches("[0-9a-f]{64}\\.apk")||file.getName().matches("download-[A-Za-z0-9_-]+\\.part"))file.delete();
            }
        }catch(IOException ignored){/* A later successful check retries managed cache cleanup. */}
    }
    static void validateManifest(JSONObject release)throws Exception {
        Object code=release.opt("version_code"),bytes=release.opt("bytes");
        if(!"net.karenax.fred".equals(release.optString("package"))
                ||!release.optString("version").matches("[0-9]+\\.[0-9]+\\.[0-9]+")
                ||!(code instanceof Integer||code instanceof Long)||((Number)code).longValue()<1
                ||!(bytes instanceof Integer||bytes instanceof Long)||((Number)bytes).longValue()<1||((Number)bytes).longValue()>MAX_BYTES
                ||!release.optString("sha256").matches("[0-9a-f]{64}"))throw new IllegalArgumentException("Manifeste Android invalide.");
    }
    static long versionCode(PackageInfo info){return Build.VERSION.SDK_INT>=28?info.getLongVersionCode():info.versionCode;}
    @SuppressWarnings("deprecation")
    static android.content.pm.Signature[] signatures(PackageInfo info){
        return Build.VERSION.SDK_INT>=28&&info.signingInfo!=null?info.signingInfo.getApkContentsSigners():info.signatures;
    }
    static void validateApk(Context context,File file,JSONObject release)throws Exception {
        validateManifest(release);
        if(!file.isFile()||file.length()!=release.getLong("bytes"))throw new IllegalArgumentException("APK incomplet.");
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(InputStream input=new FileInputStream(file)){byte[] buffer=new byte[65536];int n;while((n=input.read(buffer))!=-1)digest.update(buffer,0,n);}
        StringBuilder hex=new StringBuilder();for(byte b:digest.digest())hex.append(String.format(Locale.ROOT,"%02x",b&255));
        if(!hex.toString().equals(release.getString("sha256")))throw new IllegalArgumentException("APK altéré.");
        PackageManager pm=context.getPackageManager();
        int flags=Build.VERSION.SDK_INT>=28?PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES;
        PackageInfo archive=pm.getPackageArchiveInfo(file.getAbsolutePath(),flags),installed=pm.getPackageInfo(context.getPackageName(),flags);
        validatePackage(archive,installed,release);
    }
    static void validatePackage(PackageInfo archive,PackageInfo installed,JSONObject release)throws Exception {
        if(archive==null||!installed.packageName.equals(archive.packageName)||!release.getString("package").equals(archive.packageName)
                ||versionCode(archive)!=release.getLong("version_code")||versionCode(archive)<=versionCode(installed)
                ||!release.getString("version").equals(archive.versionName))throw new IllegalArgumentException("APK incompatible ou version trop ancienne.");
        android.content.pm.Signature[] a=signatures(archive),b=signatures(installed);
        if(a==null||b==null||a.length!=1||b.length!=1||!a[0].equals(b[0]))throw new IllegalArgumentException("La signature de l’APK ne correspond pas à Fred.");
    }
    @Override public synchronized void close(){closed=true;worker.shutdownNow();}
}
