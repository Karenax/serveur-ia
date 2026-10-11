package net.karenax.fred;

import android.content.Context;
import android.content.pm.*;
import org.json.JSONObject;
import java.io.*;
import java.security.MessageDigest;
import java.util.Locale;

/** Native policy checks: integrity, signed package identity, and monotonic versions. */
final class UpdateChecks {
    interface Checked {void run()throws Exception;}
    static void rejects(Checked action)throws Exception {try{action.run();}catch(IllegalArgumentException expected){return;}throw new AssertionError("Update should be rejected");}
    static PackageInfo pkg(int version,byte signer){
        PackageInfo info=new PackageInfo();info.packageName="net.karenax.fred";info.versionCode=version;info.versionName="1.0.5";
        info.signatures=new android.content.pm.Signature[]{new android.content.pm.Signature(new byte[]{signer})};return info;
    }
    static void run(Context context,StringBuilder log)throws Exception {
        JSONObject release=Json.object("package","net.karenax.fred","version","1.0.5","version_code",6,"bytes",8,"sha256","0".repeat(64));
        AndroidUpdates.validateManifest(release);
        JSONObject invalid=Json.copy(release);invalid.put("bytes",128L*1024*1024+1);rejects(()->AndroidUpdates.validateManifest(invalid));
        AndroidUpdates.validatePackage(pkg(6,(byte)1),pkg(5,(byte)1),release);
        rejects(()->AndroidUpdates.validatePackage(pkg(6,(byte)2),pkg(5,(byte)1),release));
        rejects(()->AndroidUpdates.validatePackage(pkg(6,(byte)1),pkg(6,(byte)1),release));
        rejects(()->AndroidUpdates.validatePackage(pkg(6,(byte)1),pkg(7,(byte)1),release));
        PackageInfo other=pkg(6,(byte)1);other.packageName="other.app";rejects(()->AndroidUpdates.validatePackage(other,pkg(5,(byte)1),release));
        rejects(()->AndroidUpdates.validatePackage(null,pkg(5,(byte)1),release));
        File fixture=new File(context.getCacheDir(),"update-integrity-test.apk");
        try{
            try(FileOutputStream output=new FileOutputStream(fixture)){output.write(new byte[8]);}
            rejects(()->AndroidUpdates.validateApk(context,fixture,release));
            fixture.delete();rejects(()->AndroidUpdates.validateApk(context,fixture,release));
        }finally{fixture.delete();}
        log.append("PASS Android update manifest bounds, integrity, package identity, signature mismatch, same-version and downgrade rejection\n");
    }
}
