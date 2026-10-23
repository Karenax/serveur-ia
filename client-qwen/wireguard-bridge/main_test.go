package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestControlRequestsPassWhileDataConnectionsAreOccupied(t *testing.T) {
	release := make(chan struct{})
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/history" {
			w.WriteHeader(200)
			w.(http.Flusher).Flush()
			<-release
			return
		}
		io.WriteString(w, "ready")
	}))
	defer server.Close()
	defer close(release)
	data := &http.Transport{MaxConnsPerHost: 1}
	control := data.Clone()
	defer data.CloseIdleConnections()
	defer control.CloseIdleConnections()
	client := &http.Client{Transport: bridgeTransport{data, control}, Timeout: 2 * time.Second}
	held, err := client.Get(server.URL + "/v1/history")
	if err != nil {
		t.Fatal(err)
	}
	defer held.Body.Close()
	for _, path := range []string{"/v1/models", "/v1/status", "/v1/device", "/v1/cancel", "/v1/voice/cancel"} {
		response, err := client.Get(server.URL + path)
		if err != nil {
			t.Fatalf("control request blocked by the data stream: %s: %v", path, err)
		}
		body, err := io.ReadAll(response.Body)
		response.Body.Close()
		if err != nil || string(body) != "ready" {
			t.Fatalf("control response: %q: %v", body, err)
		}
	}
}
