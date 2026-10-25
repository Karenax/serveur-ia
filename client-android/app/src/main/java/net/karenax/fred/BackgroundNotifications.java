package net.karenax.fred;

import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.ComponentName;
import android.content.Context;
import org.json.JSONObject;

/** Optional Android-managed polling. Android controls timing; no exact-delivery promise. */
final class BackgroundNotifications {
    static final Object LOCK=new Object();
    static final int JOB=0x4b1a01;
    static boolean enabled(Context context,String identity)throws Exception {
        JSONObject value=new SecureStore(context).read(identity+".background-alerts");
        return value!=null&&value.optBoolean("enabled",false);
    }
    static void setEnabled(Context context,String identity,boolean enabled)throws Exception {
        synchronized(LOCK){
            new SecureStore(context).write(identity+".background-alerts",Json.object("enabled",enabled));
            JobScheduler scheduler=context.getSystemService(JobScheduler.class);
            if(!enabled){scheduler.cancel(JOB);return;}
            JobInfo job=new JobInfo.Builder(JOB,new ComponentName(context,NotificationJob.class))
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPeriodic(15*60*1000L)
                .setPersisted(true).build();
            if(scheduler.schedule(job)!=JobScheduler.RESULT_SUCCESS){
                new SecureStore(context).write(identity+".background-alerts",Json.object("enabled",false));
                throw new IllegalStateException("Android n’a pas programmé les alertes. Réessayez.");
            }
        }
    }
}
