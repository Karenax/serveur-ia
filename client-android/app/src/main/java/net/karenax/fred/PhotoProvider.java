package net.karenax.fred;

import android.content.*;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.*;

/** One random, temporary photo per URI. No access to profiles or arbitrary paths. */
public final class PhotoProvider extends ContentProvider {
    static File file(Context context,Uri uri)throws IOException {
        if(!"content".equals(uri.getScheme())||!(context.getPackageName()+".photos").equals(uri.getAuthority())||uri.getPathSegments().size()!=1||!uri.getLastPathSegment().matches("[a-f0-9]{32}\\.jpg"))throw new FileNotFoundException("Photo indisponible.");
        File root=new File(context.getCacheDir(),"captures").getCanonicalFile();
        File target=new File(root,uri.getLastPathSegment()).getCanonicalFile();
        if(!root.equals(target.getParentFile()))throw new FileNotFoundException("Photo indisponible.");
        return target;
    }
    static Uri create(Context context)throws IOException {
        File root=new File(context.getCacheDir(),"captures");if(!root.exists()&&!root.mkdirs())throw new IOException("Capture indisponible.");
        File[] files=root.listFiles();if(files!=null)for(File f:files)if(f.getName().matches("[a-f0-9]{32}\\.jpg")&&System.currentTimeMillis()-f.lastModified()>3600000L)f.delete();
        Uri uri=Uri.parse("content://"+context.getPackageName()+".photos/"+java.util.UUID.randomUUID().toString().replace("-","")+".jpg");
        if(!file(context,uri).createNewFile())throw new IOException("Capture indisponible.");return uri;
    }
    @Override public boolean onCreate(){return true;}
    @Override public String getType(Uri uri){return "image/jpeg";}
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException {
        try{return ParcelFileDescriptor.open(file(getContext(),uri),ParcelFileDescriptor.parseMode(mode));}
        catch(IOException e){throw new FileNotFoundException("Photo indisponible.");}
    }
    @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String sort){
        try{File f=file(getContext(),uri);String[] columns=projection==null?new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;MatrixCursor result=new MatrixCursor(columns);Object[] values=new Object[columns.length];for(int i=0;i<columns.length;i++)values[i]=OpenableColumns.DISPLAY_NAME.equals(columns[i])?f.getName():OpenableColumns.SIZE.equals(columns[i])?f.length():null;result.addRow(values);return result;}
        catch(IOException e){return null;}
    }
    @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
    @Override public int update(Uri uri,ContentValues values,String selection,String[] args){throw new UnsupportedOperationException();}
    @Override public int delete(Uri uri,String selection,String[] args){throw new UnsupportedOperationException();}
}
