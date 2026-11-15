package net.karenax.fred;

import java.io.*;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.regex.Pattern;

/** A verified original staged in private cache before the document picker opens. */
final class OriginalDownload implements AutoCloseable {
    private static final Pattern EXTENDED_NAME=Pattern.compile("(?:^|;)\\s*filename\\*=UTF-8''([^;]+)",Pattern.CASE_INSENSITIVE);
    private static final Pattern QUOTED_NAME=Pattern.compile("(?:^|;)\\s*filename=\"([^\"]+)\"",Pattern.CASE_INSENSITIVE);
    final File file;
    final String filename,mime;

    private OriginalDownload(File file,String filename,String mime) {
        this.file=file;this.filename=filename;this.mime=mime;
    }

    static boolean route(String path) {
        return path!=null&&(path.matches("/v1/sources/[A-Za-z0-9_-]{1,128}/raw")
            ||path.matches("/api/v1/workspace/sources/[A-Za-z0-9_-]{1,128}/original"));
    }

    static OriginalDownload prepare(Remote remote,File cache,String path,String suggestedName)throws Exception {
        File file=File.createTempFile("kiara-original-",".download",cache);
        boolean saved=false;
        Remote.Response response=null;
        remote.active.incrementAndGet();
        try {
            response=remote.open("GET","/v1/business"+path,null,null);
            if(response.status==401||response.status==403)throw new IOException("Accès à l’original refusé.");
            if(response.status==404)throw new IOException("L’original est introuvable.");
            if(response.status!=200||response.connection==null)throw new IOException("L’original est indisponible.");
            long expected=response.connection.getContentLengthLong();
            if(expected>cache.getUsableSpace())throw new IOException("Espace insuffisant pour télécharger l’original.");
            String sha=response.connection.getHeaderField("X-Agent-Source-Sha256");
            MessageDigest digest=MessageDigest.getInstance("SHA-256");
            long size=0;
            try(OutputStream output=new FileOutputStream(file)) {
                byte[] block=new byte[65536];
                int count;
                while((count=response.input.read(block))!=-1) {
                    output.write(block,0,count);
                    digest.update(block,0,count);
                    size+=count;
                }
            }
            if(expected>=0&&size!=expected)throw new IOException("Le téléchargement est incomplet. Réessayez.");
            if(sha!=null&&sha.matches("[A-Fa-f0-9]{64}")) {
                StringBuilder actual=new StringBuilder(64);
                for(byte value:digest.digest())actual.append(String.format(Locale.ROOT,"%02x",value&255));
                if(!sha.equalsIgnoreCase(actual.toString()))throw new IOException("L’empreinte de l’original ne correspond pas.");
            }
            String filename=filename(response.connection.getHeaderField("Content-Disposition"),suggestedName);
            String mime=response.type==null?"":response.type.split(";",2)[0].trim();
            if(!mime.matches("[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+"))mime="application/octet-stream";
            saved=true;
            return new OriginalDownload(file,filename,mime);
        }finally{
            if(response!=null)remote.finished(response);
            remote.active.decrementAndGet();
            if(!saved)file.delete();
        }
    }

    private static String filename(String disposition,String fallback) {
        String value=fallback==null?"":fallback;
        if(disposition!=null){
            var quoted=QUOTED_NAME.matcher(disposition);
            if(quoted.find())value=quoted.group(1);
            var encoded=EXTENDED_NAME.matcher(disposition);
            if(encoded.find())try{value=URLDecoder.decode(encoded.group(1).replace("+","%2B"),StandardCharsets.UTF_8.name());}
            catch(IllegalArgumentException|UnsupportedEncodingException ignored){}
        }
        value=value.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]","_").trim();
        if(value.isEmpty()||value.equals(".")||value.equals(".."))return "original";
        if(value.length()>180)value=value.substring(0,180);
        return value;
    }

    @Override public void close(){file.delete();}
}
