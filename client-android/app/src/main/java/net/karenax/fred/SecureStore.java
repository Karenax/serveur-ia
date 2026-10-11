package net.karenax.fred;

import android.content.Context;
import android.security.keystore.*;
import android.util.AtomicFile;
import org.json.*;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.Arrays;

/** Every personal file is encrypted before the atomic replace, never in WebView storage. */
final class SecureStore {
    private static final String ALIAS="fred-client-v1";
    private final File directory;
    SecureStore(Context context) { this(context,"vault"); }
    SecureStore(Context context,String namespace) {if(!namespace.matches("[a-z-]{1,30}"))throw new IllegalArgumentException("Stockage invalide.");directory=new File(context.getNoBackupFilesDir(),namespace);directory.mkdirs();}
    private static synchronized SecretKey key() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if(!store.containsAlias(ALIAS)){
            KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setRandomizedEncryptionRequired(true).build());generator.generateKey();
        }
        return (SecretKey)store.getKey(ALIAS,null);
    }
    private AtomicFile file(String name) { if(!name.matches("[a-z0-9.-]{1,100}"))throw new IllegalArgumentException("Nom local invalide.");return new AtomicFile(new File(directory,name+".aes")); }
    synchronized byte[] raw(String name) throws IOException { AtomicFile file=file(name);if(!file.getBaseFile().exists())return null;try(InputStream input=file.openRead()){return readBounded(input,12*1024*1024);} }
    synchronized JSONObject read(String name) throws Exception {
        byte[] raw=raw(name);if(raw==null)return null;
        if(raw.length<30||raw[0]!=1)throw new IOException("Fichier chiffré illisible ; l’original est conservé.");
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Arrays.copyOfRange(raw,1,13)));cipher.updateAAD(name.getBytes(StandardCharsets.UTF_8));
        try { return new JSONObject(new String(cipher.doFinal(Arrays.copyOfRange(raw,13,raw.length)),StandardCharsets.UTF_8)); }
        catch(Exception error){throw new IOException("Fichier chiffré illisible ; l’original est conservé.");}
    }
    synchronized String write(String name,JSONObject value) throws Exception {
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());cipher.updateAAD(name.getBytes(StandardCharsets.UTF_8));byte[] encrypted=cipher.doFinal(Json.bytes(value));
        ByteArrayOutputStream output=new ByteArrayOutputStream();output.write(1);output.write(cipher.getIV());output.write(encrypted);byte[] raw=output.toByteArray();writeRaw(name,raw);return Json.hash(raw);
    }
    synchronized void writeRaw(String name,byte[] bytes) throws IOException { AtomicFile file=file(name);FileOutputStream out=null;try { out=file.startWrite();out.write(bytes);out.getFD().sync();file.finishWrite(out); } catch(IOException e){if(out!=null)file.failWrite(out);throw e;} }
    synchronized String revision(String name) throws IOException { byte[] raw=raw(name);return raw==null?"":Json.hash(raw); }
    synchronized void delete(String name){file(name).delete();}
    static byte[] readBounded(InputStream input,int limit) throws IOException { ByteArrayOutputStream output=new ByteArrayOutputStream();byte[] buffer=new byte[16384];int n;while((n=input.read(buffer))!=-1){if(output.size()+n>limit)throw new IOException("Fichier trop volumineux.");output.write(buffer,0,n);}return output.toByteArray(); }
}
