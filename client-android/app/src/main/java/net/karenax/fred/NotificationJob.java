package net.karenax.fred;

import android.app.job.JobParameters;
import android.app.job.JobService;
import org.json.JSONArray;
import org.json.JSONObject;

/** Polls only the private inbox; no microphone, model inference or history replay. */
public final class NotificationJob extends JobService {
    private volatile Remote active;
    private volatile boolean stopped;
    private volatile int generation;
    @Override public boolean onStartJob(JobParameters parameters){
        stopped=false;final int token=++generation;
        new Thread(()->{
            boolean retry=false;
            Remote opened=null;
            try{
                SecureStore store=new SecureStore(this);JSONObject profile=store.read("profile");
                if(profile==null)return;
                Profile.validate(profile);String identity=Profile.identity(profile);
                if(!BackgroundNotifications.enabled(this,identity))return;
                NativeNotifications notifications=new NativeNotifications(this,store,identity);
                if(!notifications.enabled()||!notifications.permitted())return;
                JSONObject settings=store.read(identity+".settings");
                Remote remote=new Remote(this,profile,settings==null?new JSONObject():settings,false,store);
                opened=remote;if(token!=generation){remote.close();return;}active=remote;long cursor=0;JSONArray collected=new JSONArray();
                for(int page=0;page<11&&!stopped&&token==generation;page++){
                    JSONObject payload=remote.json("/v1/notifications/action",Json.object("action","list","after",cursor,"limit",100));
                    if(stopped||token!=generation||!BackgroundNotifications.enabled(this,identity))break;
                    JSONArray items=payload.optJSONArray("items");
                    if(items!=null)for(int i=0;i<items.length();i++)collected.put(items.getJSONObject(i));
                    if(!payload.optBoolean("has_more")){payload.put("items",collected);synchronized(BackgroundNotifications.LOCK){notifications.receive(payload);}}
                    if(items!=null&&items.length()>0){JSONArray ids=new JSONArray();for(int i=0;i<items.length();i++)ids.put(items.getJSONObject(i).getString("id"));remote.json("/v1/notifications/action",Json.object("action","delivered","ids",ids));}
                    if(!payload.optBoolean("has_more"))break;
                    cursor=payload.getLong("cursor");
                }
            }catch(Remote.HttpError e){
                retry=e.status!=401&&e.status!=403;
                if(!retry){try{SecureStore store=new SecureStore(this);JSONObject p=store.read("profile");if(p!=null)new NativeNotifications(this,store,Profile.identity(p)).revoke();}catch(Exception ignored){}}
            }catch(Exception ignored){retry=true;}
            finally{if(active==opened)active=null;if(opened!=null)opened.close();if(!stopped&&token==generation)jobFinished(parameters,retry);}
        },"kiara-background-inbox").start();
        return true;
    }
    @Override public boolean onStopJob(JobParameters parameters){stopped=true;generation++;Remote remote=active;if(remote!=null)remote.close();return true;}
}
