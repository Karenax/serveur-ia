package net.karenax.fred;
import org.json.JSONObject;
/** No test data or transport is included in the release APK. */
final class DemoTransport {
    DemoTransport(SecureStore store){throw new IllegalStateException("Démonstration indisponible.");}
    static JSONObject profile(){throw new IllegalStateException("Démonstration indisponible.");}
    int requestCount(){return 0;}
    Remote.Response open(String path,byte[] body,String requestId){throw new IllegalStateException("Démonstration indisponible.");}
}
