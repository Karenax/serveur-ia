package net.karenax.fred;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import android.util.Base64;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/** Targeted real native proxy + WireGuard test with an isolated synthetic access. */
public final class CorrectorTransportInstrumentation extends Instrumentation {
    private Bundle arguments;
    @Override public void onCreate(Bundle args) { super.onCreate(args); arguments = args; start(); }
    @Override public void onStart() {
        Bundle result = new Bundle();
        StringBuilder log = new StringBuilder();
        try {
            JSONObject profile = Profile.validate(new JSONObject(new String(Base64.decode(
                    arguments.getString("fred_profile_b64"), Base64.DEFAULT), StandardCharsets.UTF_8)));
            SecureStore store = new SecureStore(getTargetContext(), "corrector-transport-test-vault");
            try (ClientBackend client = new ClientBackend(getTargetContext(), store, profile, false)) {
                client.selectMode("wireguard");
                try (LoopbackServer local = new LoopbackServer(getTargetContext(), client)) {
                    if (!client.remote.check().optBoolean("connected")) throw new AssertionError("Synthetic tunnel unavailable");
                    for (String mode : new String[]{"correct", "professional", "friendly"}) {
                        HttpURLConnection request = (HttpURLConnection) new URL(local.origin() + "/v1/chat/completions").openConnection();
                        try {
                            request.setRequestMethod("POST"); request.setDoOutput(true);
                            request.setConnectTimeout(15000); request.setReadTimeout(30000);
                            request.setRequestProperty("Authorization", "Bearer " + client.key);
                            request.setRequestProperty("Content-Type", "application/json");
                            request.setRequestProperty("X-Qwen-Request", java.util.UUID.randomUUID().toString().replace("-", ""));
                            byte[] body = Json.bytes(Json.object("stream", true, "text_transform",
                                    Json.object("mode", mode, "text", "Texte synthétique Android à transformer.")));
                            request.setFixedLengthStreamingMode(body.length);
                            try (OutputStream output = request.getOutputStream()) { output.write(body); }
                            if (request.getResponseCode() != 200 || !request.getContentType().startsWith("text/event-stream"))
                                throw new AssertionError("Native corrector response rejected for " + mode);
                            boolean done = false; StringBuilder text = new StringBuilder();
                            try (BufferedReader input = new BufferedReader(new InputStreamReader(request.getInputStream(), StandardCharsets.UTF_8))) {
                                String line;
                                while ((line = input.readLine()) != null) {
                                    if (line.equals("data: [DONE]")) { done = true; continue; }
                                    if (line.startsWith("data: ")) text.append(new JSONObject(line.substring(6)).getJSONArray("choices")
                                            .getJSONObject(0).getJSONObject("delta").optString("content"));
                                }
                            }
                            if (!done || !text.toString().contains("Connexion Android WireGuard vérifiée"))
                                throw new AssertionError("Native SSE did not finish for " + mode);
                            log.append("PASS direct corrector ").append(mode).append(": native proxy, authenticated real WireGuard, SSE DONE\n");
                        } finally { request.disconnect(); }
                    }
                }
            } finally { store.delete(Profile.identity(profile) + ".settings"); }
            result.putString("stream", log + "ALL CORRECTOR TRANSPORT CHECKS PASSED\n");
            result.putBoolean("passed", true); finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            // Synthetic credentials and request bodies never enter the report.
            result.putString("stream", log + "FAIL " + error.getClass().getSimpleName() + "\n");
            result.putBoolean("passed", false); finish(Activity.RESULT_CANCELED, result);
        }
    }
}
