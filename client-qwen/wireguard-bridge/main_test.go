package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/netip"
	"testing"
	"time"
)

func TestRecipeBindOnlyListensOnLoopback(t *testing.T) {
	bind := udpBind(true).(*loopbackBind)
	_, _, err := bind.Open(0)
	if err != nil {
		t.Fatal(err)
	}
	defer bind.Close()
	address, err := netip.ParseAddrPort(bind.socket.LocalAddr().String())
	if err != nil || address.Addr() != netip.MustParseAddr("127.0.0.1") {
		t.Fatalf("unexpected local address: %v", bind.socket.LocalAddr())
	}
	peer, err := bind.ParseEndpoint("192.0.2.1:51820")
	if err != nil || bind.Send([][]byte{{1}}, peer) == nil {
		t.Fatal("recipe bind accepted a non-loopback destination")
	}
}

func TestBusinessRoutesAndHeaders(t *testing.T) {
	for _, method := range []string{"GET", "POST", "PUT", "PATCH", "DELETE"} {
		request := httptest.NewRequest(method, "http://localhost/v1/business/api/v1/projects?search=a", nil)
		if !businessRoute(request) {
			t.Fatalf("business route rejected: %s", method)
		}
	}
	for _, target := range []string{"/v1/business", "/v1/business-other/api", "/v1/workspace"} {
		if businessRoute(httptest.NewRequest("GET", "http://localhost"+target, nil)) {
			t.Fatalf("unrelated route accepted: %s", target)
		}
	}
	if businessRoute(httptest.NewRequest("TRACE", "http://localhost/v1/business/api/v1/projects", nil)) {
		t.Fatal("unsupported method accepted")
	}
	in := http.Header{"Content-Type": {"multipart/form-data; boundary=test"}, "Range": {"bytes=0-9"}, "Authorization": {"secret"}}
	out := http.Header{}
	copyBusinessHeaders(out, in)
	if out.Get("Content-Type") != "multipart/form-data; boundary=test" || out.Get("Range") != "bytes=0-9" || out.Get("Authorization") != "" {
		t.Fatalf("unexpected forwarded headers: %v", out)
	}
}

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
