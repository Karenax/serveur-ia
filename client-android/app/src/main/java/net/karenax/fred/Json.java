package net.karenax.fred;

import org.json.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

final class Json {
    static JSONObject object(Object... fields) {
        JSONObject result=new JSONObject();
        try { for(int i=0;i<fields.length;i+=2) result.put((String)fields[i],fields[i+1]==null?JSONObject.NULL:fields[i+1]); }
        catch(JSONException error) { throw new IllegalArgumentException(error); }
        return result;
    }
    static JSONObject copy(JSONObject value) { try { return new JSONObject(value.toString()); } catch(JSONException e){throw new IllegalArgumentException(e);} }
    static String token() { byte[] bytes=new byte[32];new SecureRandom().nextBytes(bytes);return android.util.Base64.encodeToString(bytes,android.util.Base64.NO_WRAP|android.util.Base64.URL_SAFE|android.util.Base64.NO_PADDING); }
    static String id() { return UUID.randomUUID().toString().replace("-", ""); }
    static byte[] bytes(JSONObject value) { return value.toString().getBytes(StandardCharsets.UTF_8); }
    static String hash(byte[] value) { try { byte[] bytes=MessageDigest.getInstance("SHA-256").digest(value);StringBuilder out=new StringBuilder();for(byte b:bytes)out.append(String.format(Locale.ROOT,"%02x",b&255));return out.toString(); } catch(NoSuchAlgorithmException e){throw new AssertionError(e);} }
    static String canonical(Object value) throws JSONException {
        if(value instanceof JSONObject){JSONObject object=(JSONObject)value;List<String> keys=new ArrayList<>();object.keys().forEachRemaining(keys::add);Collections.sort(keys);List<String> parts=new ArrayList<>();for(String key:keys)parts.add(JSONObject.quote(key)+":"+canonical(object.get(key)));return "{"+String.join(",",parts)+"}";}
        if(value instanceof JSONArray){JSONArray array=(JSONArray)value;List<String> parts=new ArrayList<>();for(int i=0;i<array.length();i++)parts.add(canonical(array.get(i)));return "["+String.join(",",parts)+"]";}
        return value instanceof String ? JSONObject.quote((String)value):String.valueOf(value);
    }
    static void keys(JSONObject value,String... allowed) { Set<String> set=new HashSet<>(Arrays.asList(allowed));value.keys().forEachRemaining(key->{if(!set.contains(key))throw new IllegalArgumentException("Champ invalide : "+key);}); }
    static String string(JSONObject value,String key,int min,int max) { Object field=value.opt(key);if(!(field instanceof String)||((String)field).length()<min||((String)field).length()>max)throw new IllegalArgumentException("Champ invalide : "+key);return (String)field; }
    static boolean bool(JSONObject value,String key,boolean fallback){Object field=value.opt(key);if(field==null)return fallback;if(!(field instanceof Boolean))throw new IllegalArgumentException("Booléen attendu : "+key);return (Boolean)field;}
}
