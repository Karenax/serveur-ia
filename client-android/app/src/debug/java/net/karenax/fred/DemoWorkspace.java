package net.karenax.fred;

import android.util.Base64;
import org.json.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Local, encrypted fixtures for emulator checks. This class is absent from release builds. */
final class DemoWorkspace {
    private final SecureStore store;
    private JSONObject data;

    DemoWorkspace(SecureStore store) throws Exception {
        this.store=store;
        data=store.read("demo.workspace");
        if(data==null){
            JSONObject project=project("Projet de démonstration");
            JSONObject note=Json.object("id",Json.id(),"project",project.getString("id"),"title","Bienvenue sur Android","text","Ce document de démonstration permet de vérifier l’édition sur téléphone et tablette.\n\nLes données de ce mode de test restent locales.","revision",1,"kind","note");
            JSONObject documents=Json.object(note.getString("id"),note);
            JSONObject job=Json.object("id",Json.id(),"project",project.getString("id"),"title","Vérifier la version mobile","state","completed","due",now(),"repeat_hours",0,"error","","result",Json.object("text","Les conversations, les projets et les documents sont disponibles dans cette démonstration locale.","sources",new JSONArray()).toString());
            data=Json.object("projects",new JSONArray().put(project),"documents",documents,"jobs",new JSONArray().put(job));
            save();
        }
    }

    synchronized JSONObject get() throws Exception {
        JSONObject copy=Json.copy(data);
        JSONArray projects=copy.getJSONArray("projects");
        JSONObject documents=copy.getJSONObject("documents");
        for(int i=0;i<projects.length();i++){
            JSONObject project=projects.getJSONObject(i);JSONArray summaries=new JSONArray();
            Iterator<String> keys=documents.keys();
            while(keys.hasNext()){
                JSONObject document=documents.getJSONObject(keys.next());
                if(project.getString("id").equals(document.getString("project")))summaries.put(Json.object("id",document.getString("id"),"title",document.getString("title"),"revision",document.getInt("revision"),"kind",document.optString("kind","note")));
            }
            project.put("documents",summaries);
        }
        copy.remove("documents");
        return copy;
    }

    synchronized JSONObject action(JSONObject request) throws Exception {
        String name=request.optString("action");JSONObject result;
        switch(name){
            case "project_create":{
                JSONObject project=project(text(request,"title",120));data.getJSONArray("projects").put(project);result=Json.object("id",project.getString("id"));break;
            }
            case "project_save":{
                JSONObject project=findProject(request.getString("id"));revision(project,request);
                project.put("title",text(request,"title",120)).put("instructions",request.optString("instructions")).put("archived",request.optBoolean("archived"));bump(project);result=Json.object("revision",project.getInt("revision"));break;
            }
            case "document_get":return Json.copy(document(request.getString("id")));
            case "document_create":case "document_upload":{
                String project=request.getString("project");findProject(project);
                String title=text(request,"title",180),content=request.optString("text"),kind="note";
                String original=null;
                if(name.equals("document_upload")){
                    original=request.getString("data");byte[] bytes=Base64.decode(original,Base64.DEFAULT);
                    if(bytes.length>2*1024*1024)throw new IllegalArgumentException("Fichier de démonstration limité à 2 Mo.");
                    boolean plain=title.toLowerCase(Locale.ROOT).endsWith(".txt")||title.toLowerCase(Locale.ROOT).endsWith(".md");
                    content=plain?new String(bytes,StandardCharsets.UTF_8):"Ce fichier a été importé dans le mode de démonstration. L’extraction Word et PDF est effectuée par le serveur en connexion réelle.";kind="upload";
                }
                String id=Json.id();JSONObject document=Json.object("id",id,"project",project,"title",title,"text",content,"revision",1,"kind",kind);
                if(original!=null)document.put("original",original);
                data.getJSONObject("documents").put(id,document);result=Json.object("id",id);break;
            }
            case "document_save":{
                JSONObject document=document(request.getString("id"));revision(document,request);document.put("title",text(request,"title",180)).put("text",request.getString("text"));bump(document);result=Json.object("revision",document.getInt("revision"));break;
            }
            case "document_delete":{
                JSONObject document=document(request.getString("id"));revision(document,request);data.getJSONObject("documents").remove(request.getString("id"));result=Json.object("deleted",true);break;
            }
            case "document_download":{
                JSONObject document=document(request.getString("id"));return Json.object("title",document.getString("title"),"data",document.optString("original",Base64.encodeToString(document.getString("text").getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)));
            }
            case "memory_create":{
                JSONObject memory=Json.object("id",Json.id(),"text",text(request,"text",2000));findProject(request.getString("project")).getJSONArray("memories").put(memory);result=Json.object("id",memory.getString("id"));break;
            }
            case "memory_save":case "memory_delete":{
                JSONArray array=null;JSONObject memory=null;int index=-1;JSONArray projects=data.getJSONArray("projects");
                for(int i=0;i<projects.length();i++){JSONArray rows=projects.getJSONObject(i).getJSONArray("memories");for(int j=0;j<rows.length();j++)if(request.getString("id").equals(rows.getJSONObject(j).getString("id"))){array=rows;memory=rows.getJSONObject(j);index=j;}}
                if(memory==null)throw new IllegalArgumentException("Mémoire introuvable.");
                if(name.equals("memory_save"))memory.put("text",text(request,"text",2000));else array.remove(index);
                result=Json.object("saved",true);break;
            }
            case "search":{
                JSONArray sources=new JSONArray();String query=request.optString("query").toLowerCase(Locale.ROOT);JSONObject docs=data.getJSONObject("documents");Iterator<String> keys=docs.keys();while(keys.hasNext()){
                    JSONObject document=docs.getJSONObject(keys.next());String body=document.getString("text");
                    if(request.optString("project").equals(document.getString("project"))&&(query.isEmpty()||body.toLowerCase(Locale.ROOT).contains(query)||document.getString("title").toLowerCase(Locale.ROOT).contains(query)))sources.put(Json.object("title",document.getString("title"),"text",body.substring(0,Math.min(1200,body.length())),"document",document.getString("id")));
                }return Json.object("sources",sources);
            }
            case "attachment_extract":{
                byte[] bytes=Base64.decode(request.getString("data"),Base64.DEFAULT);if(bytes.length>2*1024*1024)throw new IllegalArgumentException("Pièce jointe limitée à 2 Mo.");String content=new String(bytes,StandardCharsets.UTF_8);return Json.object("text",content.substring(0,Math.min(content.length(),50000)));
            }
            case "conversation_get":return Json.copy(findConversation(request.getString("id")));
            case "conversation_save":{
                String id=request.getString("id"),project=request.getString("project");JSONObject existing=null;try{existing=findConversation(id);}catch(IllegalArgumentException ignored){}
                int next=existing==null?1:existing.optInt("revision",0)+1;removeConversation(id);
                JSONObject conversation=Json.object("id",id,"project",project,"title",text(request,"title",120),"messages",request.getJSONArray("messages"),"archived",request.optBoolean("archived"),"revision",next);
                findProject(project).getJSONArray("conversations").put(conversation);result=Json.object("revision",next);break;
            }
            case "conversation_move":{
                JSONObject conversation=findConversation(request.getString("id"));String project=request.getString("project");findProject(project);removeConversation(request.getString("id"));conversation.put("project",project);bump(conversation);findProject(project).getJSONArray("conversations").put(conversation);result=Json.object("revision",conversation.getInt("revision"));break;
            }
            case "conversation_archive":{
                JSONObject conversation=findConversation(request.getString("id"));conversation.put("archived",request.optBoolean("archived"));bump(conversation);result=Json.object("revision",conversation.getInt("revision"));break;
            }
            case "conversation_delete":removeConversation(request.getString("id"));result=Json.object("deleted",true);break;
            case "job_create":{
                String project=request.getString("project");findProject(project);int delay=request.optInt("delay_minutes");String title=request.optString("title",request.optString("prompt","Tâche de démonstration"));title=title.substring(0,Math.min(120,title.length()));String id=Json.id();
                JSONObject job=Json.object("id",id,"project",project,"title",title,"state",delay>0?"queued":"completed","due",now()+delay*60L,"repeat_hours",request.optInt("repeat_hours"),"error","","result",Json.object("text","Résultat local de démonstration.\n\nDemande : "+request.optString("prompt"),"sources",new JSONArray()).toString());data.getJSONArray("jobs").put(job);result=Json.object("id",id);break;
            }
            case "job_get":return Json.copy(findJob(request.getString("id")));
            case "job_pause":case "job_cancel":case "job_retry":{
                JSONObject job=findJob(request.getString("id"));job.put("state",name.equals("job_pause")?"paused":name.equals("job_cancel")?"cancelled":"completed");result=Json.object("saved",true);break;
            }
            default:throw new IllegalArgumentException("Action de démonstration indisponible : "+name);
        }
        save();return result;
    }

    private void save() throws Exception {store.write("demo.workspace",data);}
    private static long now(){return System.currentTimeMillis()/1000L;}
    private static JSONObject project(String title){return Json.object("id",Json.id(),"title",title,"instructions","","archived",false,"revision",1,"documents",new JSONArray(),"memories",new JSONArray(),"conversations",new JSONArray());}
    private JSONObject findProject(String id) throws JSONException {JSONArray projects=data.getJSONArray("projects");for(int i=0;i<projects.length();i++)if(id.equals(projects.getJSONObject(i).getString("id")))return projects.getJSONObject(i);throw new IllegalArgumentException("Projet introuvable.");}
    private JSONObject document(String id) throws JSONException {JSONObject document=data.getJSONObject("documents").optJSONObject(id);if(document==null)throw new IllegalArgumentException("Document introuvable.");return document;}
    private JSONObject findJob(String id) throws JSONException {JSONArray jobs=data.getJSONArray("jobs");for(int i=0;i<jobs.length();i++)if(id.equals(jobs.getJSONObject(i).getString("id")))return jobs.getJSONObject(i);throw new IllegalArgumentException("Tâche introuvable.");}
    private JSONObject findConversation(String id) throws JSONException {JSONArray projects=data.getJSONArray("projects");for(int i=0;i<projects.length();i++){JSONArray rows=projects.getJSONObject(i).getJSONArray("conversations");for(int j=0;j<rows.length();j++)if(id.equals(rows.getJSONObject(j).getString("id")))return rows.getJSONObject(j);}throw new IllegalArgumentException("Conversation introuvable.");}
    private void removeConversation(String id) throws JSONException {JSONArray projects=data.getJSONArray("projects");for(int i=0;i<projects.length();i++){JSONArray rows=projects.getJSONObject(i).getJSONArray("conversations");for(int j=rows.length()-1;j>=0;j--)if(id.equals(rows.getJSONObject(j).getString("id")))rows.remove(j);}}
    private static void revision(JSONObject value,JSONObject request){if(request.optInt("revision",value.optInt("revision"))!=value.optInt("revision"))throw new IllegalArgumentException("La version de démonstration a changé. Comparez puis réessayez.");}
    private static void bump(JSONObject value) throws JSONException {value.put("revision",value.optInt("revision",0)+1);}
    private static String text(JSONObject request,String key,int max){String value=request.optString(key).trim();if(value.isEmpty()||value.length()>max)throw new IllegalArgumentException("Champ invalide : "+key);return value;}
}
