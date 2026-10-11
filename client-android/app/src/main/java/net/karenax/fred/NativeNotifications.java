package net.karenax.fred;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.Build;
import android.media.AudioAttributes;
import android.provider.Settings;
import org.json.*;
import java.util.*;

/** System alerts contain fixed public text and an opaque inbox id, never a document excerpt. */
final class NativeNotifications {
    static final String CHANNEL="fred_results", STANDARD_CHANNEL="fred_results_standard", EXTRA_ID="fred_notification_id", EXTRA_IDENTITY="fred_notification_identity";
    private final Context context;
    private final SecureStore store;
    private final String identity, filename, tag;
    private final NotificationManager manager;
    private JSONObject state;
    private boolean storageAvailable=true;
    NativeNotifications(Context context,SecureStore store,String identity)throws Exception {
        this.context=context;this.store=store;this.identity=identity;filename=identity+".notifications";tag="fred:"+identity;
        manager=(NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
        try{state=store.read(filename);if(state!=null&&(!(state.opt("enabled") instanceof Boolean)||state.optJSONArray("seen")==null||state.optJSONArray("seen").length()>1000))throw new java.io.IOException("Stockage invalide.");}catch(Exception ignored){storageAvailable=false;state=null;}
        if(state==null)state=Json.object("enabled",false,"discreet",true,"seen",new JSONArray());
    }
    static boolean validId(String value){return value!=null&&value.matches("[0-9a-f]{32}");}
    synchronized boolean enabled(){return state.optBoolean("enabled",false);}
    private String channelId(){return state.optBoolean("discreet",true)?CHANNEL:STANDARD_CHANNEL;}
    boolean permitted(){NotificationChannel channel=manager.getNotificationChannel(channelId());return (Build.VERSION.SDK_INT<33||context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED)&&manager.areNotificationsEnabled()&&(channel==null||channel.getImportance()!=NotificationManager.IMPORTANCE_NONE);}
    synchronized JSONObject status(){return Json.object("enabled",enabled(),"permitted",permitted(),"discreet",state.optBoolean("discreet",true),"storage_available",storageAvailable,"mode","connected","push",false);}
    // The global server preference is authoritative. The subscription field is
    // a compatibility fallback, never an additional veto of audible alerts.
    static boolean discreet(JSONObject payload,boolean fallback){JSONObject preferences=payload.optJSONObject("preferences");if(preferences!=null&&preferences.opt("discreet") instanceof Boolean)return preferences.optBoolean("discreet");JSONObject subscription=payload.optJSONObject("subscription");return subscription!=null&&subscription.opt("discreet") instanceof Boolean?subscription.optBoolean("discreet"):fallback;}
    synchronized void setEnabled(boolean enabled)throws Exception {if(!storageAvailable)throw new IllegalStateException("Le stockage des alertes est illisible. La boîte serveur reste disponible et le fichier local est conservé.");state.put("enabled",enabled);store.write(filename,state);if(!enabled)clear();}
    synchronized void clear(){for(android.service.notification.StatusBarNotification active:manager.getActiveNotifications())if(active.getTag()!=null&&active.getTag().startsWith(tag+"."))manager.cancel(active.getTag(),active.getId());}
    synchronized void revoke()throws Exception {setEnabled(false);}
    synchronized JSONArray receive(JSONObject payload)throws Exception {
        if(!storageAvailable){clear();return new JSONArray();}
        if(payload.optBoolean("access_revoked")){revoke();return new JSONArray();}
        if(payload.optBoolean("reset")){clear();state.put("seen",new JSONArray());store.write(filename,state);}
        state.put("discreet",discreet(payload,state.optBoolean("discreet",true)));
        JSONArray items=payload.optJSONArray("items"),reads=payload.optJSONArray("read_ids"),saved=state.optJSONArray("seen");
        LinkedHashSet<String> seen=new LinkedHashSet<>();if(saved!=null)for(int i=0;i<saved.length();i++)if(validId(saved.optString(i)))seen.add(saved.optString(i));
        JSONArray retained=payload.optJSONArray("retained_ids");if(retained!=null){Set<String> kept=new HashSet<>();for(int i=0;i<Math.min(retained.length(),1000);i++)if(validId(retained.optString(i)))kept.add(retained.optString(i));for(android.service.notification.StatusBarNotification active:manager.getActiveNotifications())if(active.getTag()!=null&&active.getTag().startsWith(tag+".")&&!kept.contains(active.getTag().substring(tag.length()+1)))manager.cancel(active.getTag(),active.getId());seen.retainAll(kept);}
        Set<String> readIds=new HashSet<>();if(reads!=null)for(int i=0;i<Math.min(reads.length(),1000);i++){String id=reads.optString(i);if(validId(id)){readIds.add(id);manager.cancel(tag+"."+id,1);seen.add(id);}}
        JSONObject subscription=payload.optJSONObject("subscription");boolean subscribed=subscription==null||subscription.optBoolean("enabled",true);
        if(!subscribed)clear();
        JSONObject preferences=payload.optJSONObject("preferences"),types=preferences==null?null:preferences.optJSONObject("types");
        for(android.service.notification.StatusBarNotification active:manager.getActiveNotifications())if(active.getTag()!=null&&active.getTag().startsWith(tag+".")&&types!=null&&!types.optBoolean(active.getNotification().extras.getString("fred.type",""),true))manager.cancel(active.getTag(),active.getId());
        JSONArray displayed=new JSONArray();String candidate="",candidateType="";java.util.List<String> announce=new ArrayList<>();
        if(items!=null)for(int i=Math.max(0,items.length()-1000);i<items.length();i++){
            JSONObject item=items.optJSONObject(i);if(item==null)continue;String id=item.optString("id");if(!validId(id))continue;
            boolean read=readIds.contains(id)||(item.has("read_at")&&!item.isNull("read_at")&&!item.optString("read_at").isEmpty()&&!"0".equals(item.optString("read_at")));
            if(read){manager.cancel(tag+"."+id,1);seen.add(id);continue;}
            String type=item.optString("type");
            if(!subscribed||!item.optBoolean("enabled",true)||types!=null&&!types.optBoolean(type,true)){manager.cancel(tag+"."+id,1);continue;}
            if(!enabled()||!permitted()||seen.contains(id))continue;
            announce.add(id);candidate=id;candidateType=type;
        }
        // Reconnection can contain hundreds of unread entries. One generic
        // system alert opens the latest result; the complete inbox stays in Fred.
        if(!candidate.isEmpty()&&!payload.optBoolean("has_more")){
            Notification value=build(candidate);value.extras.putString("fred.type",candidateType);
            try{trimActive();manager.notify(tag+"."+candidate,1,value);seen.addAll(announce);displayed.put(candidate);}catch(SecurityException ignored){}
        }
        while(seen.size()>1000)seen.remove(seen.iterator().next());
        state.put("seen",new JSONArray(seen));store.write(filename,state);return displayed;
    }
    private void trimActive(){java.util.List<android.service.notification.StatusBarNotification> active=new ArrayList<>();for(android.service.notification.StatusBarNotification item:manager.getActiveNotifications())if(item.getTag()!=null&&item.getTag().startsWith(tag+"."))active.add(item);active.sort(Comparator.comparingLong(android.service.notification.StatusBarNotification::getPostTime));while(active.size()>=20){android.service.notification.StatusBarNotification first=active.remove(0);manager.cancel(first.getTag(),first.getId());}}
    Notification build(String id){
        if(!validId(id))throw new IllegalArgumentException("Notification invalide.");
        String selectedChannel=channelId();boolean silent=selectedChannel.equals(CHANNEL);
        NotificationChannel channel=new NotificationChannel(selectedChannel,silent?"Résultats Fred · silencieux":"Résultats Fred · son Android",NotificationManager.IMPORTANCE_DEFAULT);
        channel.setDescription("Résultats lorsque le client Fred est ouvert. Le contenu privé reste masqué.");channel.setLockscreenVisibility(Notification.VISIBILITY_PRIVATE);
        if(silent){channel.enableVibration(false);channel.setSound(null,null);}else{channel.setSound(Settings.System.DEFAULT_NOTIFICATION_URI,new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_NOTIFICATION).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build());}
        // Separate channel IDs are required: Android keeps channel sound settings
        // immutable after creation and preserves any settings chosen by the user.
        manager.createNotificationChannel(channel);
        Intent intent=new Intent(context,MainActivity.class).setAction("net.karenax.fred.NOTIFICATION."+id).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP).putExtra(EXTRA_ID,id).putExtra(EXTRA_IDENTITY,identity);
        PendingIntent click=PendingIntent.getActivity(context,id.hashCode(),intent,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification publicValue=new Notification.Builder(context,selectedChannel).setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Fred").setContentText("Une notification est disponible.").build();
        return new Notification.Builder(context,selectedChannel).setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Fred · Un résultat est disponible").setContentText("Touchez pour ouvrir votre notification.").setContentIntent(click).setAutoCancel(true).setOnlyAlertOnce(true).setVisibility(Notification.VISIBILITY_PRIVATE).setPublicVersion(publicValue).setGroup("fred_results").setCategory(Notification.CATEGORY_STATUS).setShowWhen(true).build();
    }
}
