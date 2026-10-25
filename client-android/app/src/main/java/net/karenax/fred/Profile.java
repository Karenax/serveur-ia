package net.karenax.fred;

import android.util.Base64;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

final class Profile {
    static final String HTTPS="https://ia.karenax.net";
    static JSONObject validate(JSONObject value) throws JSONException {
        if(!"wireguard://10.77.0.1:8766".equals(value.optString("url"))||!"wireguard".equals(value.optString("transport")))throw new IllegalArgumentException("Profil personnel Kiara attendu.");
        int protocol=value.optInt("protocol",1);if(protocol<1||protocol>4)throw new IllegalArgumentException("Version du profil incompatible.");
        if(!value.optString("token").matches("qwen_[0-9a-f]{16}_[A-Za-z0-9_-]{43}"))throw new IllegalArgumentException("Accès serveur invalide.");
        JSONObject wg=value.optJSONObject("wireguard");if(wg==null)throw new IllegalArgumentException("Profil WireGuard absent.");
        for(String field:new String[]{"private_key","server_public_key","preshared_key"}){String encoded=wg.optString(field);if(!encoded.matches("[A-Za-z0-9+/]{43}="))throw new IllegalArgumentException("Clé WireGuard invalide.");byte[] raw=Base64.decode(encoded,Base64.NO_WRAP);if(raw.length!=32)throw new IllegalArgumentException("Clé WireGuard invalide.");}
        String address=wg.optString("address");if(!address.matches("10\\.77\\.0\\.\\d{1,3}/32"))throw new IllegalArgumentException("Adresse du tunnel invalide.");int last=Integer.parseInt(address.split("[./]")[3]);if(last<2||last>254)throw new IllegalArgumentException("Adresse du tunnel invalide.");
        endpoint(wg.optString("endpoint"));JSONArray routes=value.optJSONArray("local_routes");if(value.has("local_routes")&&routes==null||routes!=null&&routes.length()>16)throw new IllegalArgumentException("Routes locales invalides.");
        if(routes!=null)for(int i=0;i<routes.length();i++){JSONObject route=routes.getJSONObject(i);String endpoint=endpoint(route.optString("endpoint"));String host=endpoint.substring(0,endpoint.lastIndexOf(':'));String[] network=route.optString("network").split("/",-1);if(!host.matches("(?:10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|192\\.168\\.\\d{1,3}\\.\\d{1,3}|172\\.(?:1[6-9]|2\\d|3[01])\\.\\d{1,3}\\.\\d{1,3})")||network.length!=2||!network[1].matches("[0-9]|[12][0-9]|3[0-2]"))throw new IllegalArgumentException("Route locale invalide.");long addressValue=ipv4(host),networkValue=ipv4(network[0]);int bits=Integer.parseInt(network[1]);long mask=bits==0?0:0xffffffffL<<(32-bits)&0xffffffffL;if((networkValue&mask)!=networkValue||(addressValue&mask)!=networkValue)throw new IllegalArgumentException("Route locale invalide.");}
        return Json.copy(value);
    }
    static String endpoint(String value){if(value==null||value.length()>300)throw new IllegalArgumentException("Adresse WireGuard invalide.");String trimmed=value.trim();int split=trimmed.lastIndexOf(':');if(split<1)throw new IllegalArgumentException("Adresse attendue : IP-ou-DNS:port.");String host=trimmed.substring(0,split),port=trimmed.substring(split+1);if(!host.matches("[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?|\\[[0-9A-Fa-f:]+\\]")||!port.matches("[0-9]{1,5}"))throw new IllegalArgumentException("Adresse WireGuard invalide.");int number=Integer.parseInt(port);if(number<1||number>65535)throw new IllegalArgumentException("Port WireGuard invalide.");return host+":"+number;}
    static JSONObject importFile(InputStream input) throws Exception {
        // Keep only the tail of a potentially large Windows client; never execute an imported EXE.
        int cap=65552;byte[] ring=new byte[cap];long total=0;byte[] chunk=new byte[16384];int n;
        while((n=input.read(chunk))!=-1){if(total+n>256L*1024*1024)throw new IOException("Client à importer limité à 256 Mo.");for(int i=0;i<n;i++)ring[(int)((total+i)%cap)]=chunk[i];total+=n;}
        int length=(int)Math.min(total,cap);byte[] tail=new byte[length];for(int i=0;i<length;i++)tail[i]=ring[(int)((total-length+i)%cap)];
        byte[] marker="QWENPROFILE1".getBytes(StandardCharsets.US_ASCII);
        if(length>=16&&Arrays.equals(Arrays.copyOfRange(tail,length-marker.length,length),marker)){
            int start=length-16;int size=(tail[start]&255)|((tail[start+1]&255)<<8)|((tail[start+2]&255)<<16)|((tail[start+3]&255)<<24);
            if(size<1||size>65536||size>start)throw new IllegalArgumentException("Accès intégré invalide.");
            return validate(new JSONObject(new String(tail,start-size,size,StandardCharsets.UTF_8)));
        }
        if(total>65536)throw new IllegalArgumentException("Profil JSON limité à 64 Ko, ou client EXE personnel attendu.");
        String json=new String(tail,StandardCharsets.UTF_8);if(json.startsWith("\ufeff"))json=json.substring(1);return validate(new JSONObject(json));
    }
    static String identity(JSONObject profile){return Json.hash((profile.optString("url")+profile.optString("token")).getBytes(StandardCharsets.UTF_8)).substring(0,20);}
    private static long ipv4(String value){String[] parts=value.split("\\.",-1);if(parts.length!=4)throw new IllegalArgumentException("Adresse IPv4 invalide.");long result=0;for(String part:parts){if(!part.matches("0|[1-9][0-9]{0,2}"))throw new IllegalArgumentException("Adresse IPv4 invalide.");int number=Integer.parseInt(part);if(number>255)throw new IllegalArgumentException("Adresse IPv4 invalide.");result=(result<<8)|number;}return result;}
    static String name(JSONObject profile){String name=profile.optString("client_name",profile.optString("name",profile.optString("label","Accès personnel")));return name.length()>180?name.substring(0,180):name;}
}
