package net.karenax.fred;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import android.util.Base64;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

/** Isolated native catalogue, selection, history and WireGuard contract checks. */
public final class ModelSelectionInstrumentation extends Instrumentation {
    private static final String CLOUD = "fred-model-0123456789abcdef";
    private static final String SYNTHETIC_TEXT = "Test synthétique Android : modèle distant.";
    private Bundle arguments;
    @Override public void onCreate(Bundle args) { super.onCreate(args); arguments = args; start(); }
    private static void check(boolean condition) { if (!condition) throw new AssertionError("Model selection contract failed"); }
    private static JSONObject read(HttpURLConnection connection, int expected) throws Exception {
        check(connection.getResponseCode() == expected);
        try (InputStream input = expected >= 400 ? connection.getErrorStream() : connection.getInputStream()) {
            return new JSONObject(new String(SecureStore.readBounded(input, 65536), StandardCharsets.UTF_8));
        }
    }
    private static HttpURLConnection request(LoopbackServer local, ClientBackend client, String path, JSONObject body) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(local.origin() + path).openConnection();
        connection.setConnectTimeout(15000); connection.setReadTimeout(30000);
        connection.setRequestProperty("Authorization", "Bearer " + client.key);
        if (body != null) {
            connection.setRequestMethod("POST"); connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setRequestProperty("X-Qwen-Request", Json.id());
            byte[] bytes = Json.bytes(body); connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream output = connection.getOutputStream()) { output.write(bytes); }
        }
        return connection;
    }
    private static JSONObject history(String model) {
        JSONObject row = Json.object("id", "native-model-history", "title", "Modèle de test", "messages", new JSONArray());
        if (model != null) try { row.put("model", model); } catch (Exception error) { throw new AssertionError(error); }
        return Json.object("conversations", new JSONArray().put(row), "currentId", "native-model-history");
    }
    @Override public void onStart() {
        Bundle result = new Bundle(); StringBuilder log = new StringBuilder();
        try {
            JSONObject profile = Profile.validate(new JSONObject(new String(Base64.decode(
                    arguments.getString("fred_profile_b64"), Base64.DEFAULT), StandardCharsets.UTF_8)));
            SecureStore store = new SecureStore(getTargetContext(), "model-selection-test-vault");
            String identity = Profile.identity(profile);
            try (ClientBackend client = new ClientBackend(getTargetContext(), store, profile, false)) {
                client.selectMode("wireguard");
                try (LoopbackServer local = new LoopbackServer(getTargetContext(), client)) {
                    HttpURLConnection request = request(local, client, "/v1/models", null);
                    JSONObject catalogue;
                    try { catalogue = read(request, 200); } finally { request.disconnect(); }
                    JSONArray rows = catalogue.getJSONArray("data");
                    check(rows.length() == 2 && "hermes".equals(catalogue.getString("source"))
                            && CLOUD.equals(catalogue.getString("default_model")));
                    JSONObject localModel = rows.getJSONObject(0), cloud = rows.getJSONObject(1);
                    check("fred-qwen".equals(localModel.getString("id")) && !localModel.getBoolean("available")
                            && CLOUD.equals(cloud.getString("id")) && cloud.getBoolean("available")
                            && "OpenRouter".equals(cloud.getString("provider")) && "Fixture cloud".equals(cloud.getString("label"))
                            && cloud.getJSONObject("capabilities").getBoolean("images")
                            && cloud.getJSONObject("capabilities").getInt("context_length") == 131072);
                    check(!catalogue.has("api_key") && !cloud.has("api_key") && !cloud.has("base_url")
                            && client.remote.state().getBoolean("connected") && CLOUD.equals(client.remote.state().getString("model")));
                    log.append("PASS public native catalogue: provider, label, capabilities, default; Qwen unloaded and cloud available\n");

                    request = request(local, client, "/v1/chat/completions", Json.object("stream", true, "text_transform",
                            Json.object("mode", "correct", "text", "Texte synthétique Android à transformer.")));
                    try { check("model_unloaded".equals(read(request, 503).getJSONObject("error").getString("code"))); }
                    finally { request.disconnect(); }
                    check(client.remote.state().getBoolean("connected") && CLOUD.equals(client.remote.state().getString("model")));
                    log.append("PASS direct-corrector local-unloaded error preserves connection to available cloud model\n");

                    JSONObject saved = HistorySync.validate(history(CLOUD));
                    store.write(identity + ".history", saved);
                    HistorySync reload = new HistorySync(store, client.remote, identity);
                    check(CLOUD.equals(reload.read().getJSONObject("history").getJSONArray("conversations").getJSONObject(0).getString("model")));
                    HistorySync.validate(history(null));
                    for (Object invalid : new Object[]{JSONObject.NULL, true, "", "   ", new String(new char[513]).replace('\0', 'x')}) {
                        JSONObject bad = history(null); bad.getJSONArray("conversations").getJSONObject(0).put("model", invalid);
                        boolean rejected = false; try { HistorySync.validate(bad); } catch (IllegalArgumentException expected) { rejected = true; }
                        check(rejected);
                    }
                    JSONObject left = history(CLOUD).getJSONArray("conversations").getJSONObject(0);
                    JSONObject right = Json.copy(left); right.put("model", "fred-qwen");
                    left.getJSONArray("messages").put(Json.object("role", "user", "content", "Fixture", "turn_id", "native-model-turn"));
                    right.put("messages", new JSONArray(left.getJSONArray("messages").toString()).put(Json.object("role", "assistant", "content", "Fixture", "turn_id", "native-model-turn")));
                    check(HistorySync.authoritativeTurns(left, right) == null);
                    right.put("model", CLOUD); check(HistorySync.authoritativeTurns(left, right) != null);
                    log.append("PASS encrypted conversation model survives reload; legacy histories accepted; invalid values and conflicting model merge rejected\n");

                    JSONArray messages = new JSONArray().put(Json.object("role", "user", "content", SYNTHETIC_TEXT));
                    request = request(local, client, "/v1/context", Json.object("model", CLOUD, "messages", messages));
                    try {
                        JSONObject context = read(request, 200);
                        check(context.getBoolean("estimated") && context.getInt("capacity") == 131072);
                    } finally { request.disconnect(); }
                    log.append("PASS selected model forwarded intact in native context POST; remote-provider context estimate returned\n");

                    request = request(local, client, "/v1/chat/completions", Json.object("model", CLOUD, "stream", true,
                            "conversation_id", Json.id(), "messages", messages));
                    try {
                        check(request.getResponseCode() == 200 && request.getContentType().startsWith("text/event-stream"));
                        boolean done = false; StringBuilder text = new StringBuilder();
                        try (BufferedReader input = new BufferedReader(new InputStreamReader(request.getInputStream(), StandardCharsets.UTF_8))) {
                            String line;
                            while ((line = input.readLine()) != null) {
                                if (line.equals("data: [DONE]")) done = true;
                                else if (line.startsWith("data: ")) text.append(new JSONObject(line.substring(6)).getJSONArray("choices").getJSONObject(0).getJSONObject("delta").optString("content"));
                            }
                        }
                        check(done && text.toString().contains("Connexion Android WireGuard vérifiée"));
                    } finally { request.disconnect(); }
                    log.append("PASS selected model forwarded intact in native chat POST through authenticated WireGuard; complete SSE response\n");

                    request = request(local, client, "/v1/models", null);
                    try {
                        JSONObject unavailable = read(request, 200);
                        check(unavailable.getJSONArray("data").length() == 2 && !unavailable.getJSONArray("data").getJSONObject(1).getBoolean("available"));
                        check(client.remote.state().getBoolean("reachable") && !client.remote.state().getBoolean("connected"));
                    } finally { request.disconnect(); }
                    request = request(local, client, "/v1/context", Json.object("model", "fred-model-retired", "messages", messages));
                    try { check("model_unavailable".equals(read(request, 503).getJSONObject("error").getString("code"))); }
                    finally { request.disconnect(); }
                    check(CLOUD.equals(reload.read().getJSONObject("history").getJSONArray("conversations").getJSONObject(0).getString("model")));
                    log.append("PASS unavailable catalogue remains HTTP 200; retired selection returns explicit error without fallback or history rewrite\n");
                }
            } finally {
                for (String suffix : new String[]{".settings", ".history", ".history.sync"}) store.delete(identity + suffix);
            }
            result.putString("stream", log + "ALL MODEL SELECTION CHECKS PASSED\n");
            result.putBoolean("passed", true); finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            result.putString("stream", log + "FAIL " + error.getClass().getSimpleName() + "\n");
            result.putBoolean("passed", false); finish(Activity.RESULT_CANCELED, result);
        }
    }
}
