package net.karenax.fred;

import android.content.Context;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

/** Per-app WireGuard network stack: no system VPN, secrets only through process stdin. */
final class WireGuardBridge implements AutoCloseable {
    private Process process;
    private String baseUrl;
    private final String bridgeKey;

    WireGuardBridge(Context context, JSONObject profile, String endpoint) throws Exception {
        byte[] random = new byte[32];
        new SecureRandom().nextBytes(random);
        bridgeKey = android.util.Base64.encodeToString(random, android.util.Base64.URL_SAFE | android.util.Base64.NO_WRAP | android.util.Base64.NO_PADDING);
        File executable = new File(context.getApplicationInfo().nativeLibraryDir, "libfredwireguard.so");
        if (!executable.isFile()) throw new IOException("Le moteur WireGuard Android est absent pour cet appareil.");
        ExecutorService readiness = Executors.newSingleThreadExecutor();
        try {
            process = new ProcessBuilder(executable.getAbsolutePath()).start();
            Thread stderr = new Thread(() -> {
                try { byte[] buffer = new byte[1024]; while (process.getErrorStream().read(buffer) >= 0) {} }
                catch (IOException ignored) {}
            }, "WireGuard-stderr");
            stderr.setDaemon(true);
            stderr.start();
            JSONObject wireguard = new JSONObject(profile.getJSONObject("wireguard").toString());
            wireguard.put("endpoint", endpoint);
            JSONObject configuration = new JSONObject()
                    .put("wireguard", wireguard)
                    .put("api_token", profile.getString("token"))
                    .put("bridge_token", bridgeKey);
            process.getOutputStream().write((configuration.toString() + "\n").getBytes(StandardCharsets.UTF_8));
            process.getOutputStream().flush();
            Future<String> ready = readiness.submit(() -> {
                BufferedReader output = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
                StringBuilder line = new StringBuilder();
                int character;
                while ((character = output.read()) != -1 && character != '\n') {
                    if (line.length() >= 8192) throw new IOException("Réponse WireGuard invalide.");
                    line.append((char) character);
                }
                return line.toString();
            });
            JSONObject state = new JSONObject(ready.get(20, TimeUnit.SECONDS));
            int port = state.optInt("port", 0);
            if (!state.optBoolean("ready") || port < 1 || port > 65535)
                throw new IOException("WireGuard ne démarre pas. Vérifier les paramètres d'accès.");
            baseUrl = "http://127.0.0.1:" + port;
        } catch (Exception error) {
            close();
            throw new IOException("Le tunnel WireGuard ne démarre pas sur cet appareil.", error);
        } finally { readiness.shutdownNow(); }
    }

    String getBaseUrl() { return baseUrl; }
    String getBridgeKey() { return bridgeKey; }
    boolean isAlive() { return process != null && process.isAlive(); }

    JSONObject status() {
        if (!isAlive() || baseUrl == null) return new JSONObject();
        HttpURLConnection request = null;
        try {
            request = (HttpURLConnection) new URL(baseUrl + "/bridge/status").openConnection();
            request.setInstanceFollowRedirects(false);
            request.setConnectTimeout(2000);
            request.setReadTimeout(2000);
            request.setRequestProperty("X-Qwen-Bridge", bridgeKey);
            if (request.getResponseCode() != 200) return new JSONObject();
            StringBuilder value = new StringBuilder();
            try (BufferedReader stream = new BufferedReader(new InputStreamReader(request.getInputStream(), StandardCharsets.UTF_8))) {
                char[] buffer = new char[1024]; int count;
                while ((count = stream.read(buffer)) != -1) {
                    if (value.length() + count > 8192) return new JSONObject();
                    value.append(buffer, 0, count);
                }
            }
            return new JSONObject(value.toString());
        } catch (Exception ignored) { return new JSONObject(); }
        finally { if (request != null) request.disconnect(); }
    }

    @Override public void close() {
        if (process == null) return;
        try { process.getOutputStream().close(); } catch (IOException ignored) {}
        try {
            if (!process.waitFor(2, TimeUnit.SECONDS)) process.destroy();
            if (!process.waitFor(1, TimeUnit.SECONDS)) process.destroyForcibly();
        } catch (InterruptedException interrupted) {
            process.destroyForcibly();
            Thread.currentThread().interrupt();
        }
    }
}
