// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Qwen Server contributors.
package main

import (
	"context"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/netip"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/tun/netstack"
)

type WireGuard struct {
	PrivateKey      string `json:"private_key"`
	ServerPublicKey string `json:"server_public_key"`
	PresharedKey    string `json:"preshared_key"`
	Address         string `json:"address"`
	Endpoint        string `json:"endpoint"`
}
type Config struct {
	Role         string    `json:"role"`
	WireGuard    WireGuard `json:"wireguard"`
	APIToken     string    `json:"api_token"`
	BridgeToken  string    `json:"bridge_token"`
	ListenPort   int       `json:"listen_port"`
	UpstreamPort int       `json:"upstream_port"`
	Peers        []Peer    `json:"peers"`
}
type Peer struct {
	PublicKey    string `json:"public_key"`
	PresharedKey string `json:"preshared_key"`
	Address      string `json:"address"`
}

func peerCommands(peers []Peer, previous map[string]Peer) (string, map[string]Peer, error) {
	next := map[string]Peer{}
	var commands strings.Builder
	if len(peers) > 100 {
		return "", nil, fmt.Errorf("trop de clients")
	}
	addresses := map[string]bool{}
	for _, p := range peers {
		prefix, e := netip.ParsePrefix(p.Address)
		if e != nil || prefix.Bits() != 32 || !netip.MustParsePrefix("10.77.0.0/24").Contains(prefix.Addr()) || prefix.Addr().As4()[3] < 2 || prefix.Addr().As4()[3] > 254 || addresses[p.Address] {
			return "", nil, fmt.Errorf("adresse client invalide")
		}
		addresses[p.Address] = true
		public, e := keyHex(p.PublicKey)
		if e != nil {
			return "", nil, e
		}
		psk, e := keyHex(p.PresharedKey)
		if e != nil {
			return "", nil, e
		}
		if _, found := next[p.PublicKey]; found {
			return "", nil, fmt.Errorf("client en double")
		}
		next[p.PublicKey] = p
		if old, found := previous[p.PublicKey]; !found || old != p {
			fmt.Fprintf(&commands, "public_key=%s\npreshared_key=%s\nreplace_allowed_ips=true\nallowed_ip=%s\n", public, psk, p.Address)
		}
	}
	for public := range previous {
		if _, found := next[public]; !found {
			value, _ := keyHex(public)
			fmt.Fprintf(&commands, "public_key=%s\nremove=true\n", value)
		}
	}
	return commands.String(), next, nil
}

func runServer(cfg Config, decoder *json.Decoder) error {
	private, e := keyHex(cfg.WireGuard.PrivateKey)
	if e != nil || cfg.ListenPort < 0 || cfg.ListenPort > 65535 || cfg.UpstreamPort < 1 || cfg.UpstreamPort > 65535 {
		return fmt.Errorf("configuration du serveur invalide")
	}
	commands, peers, e := peerCommands(cfg.Peers, map[string]Peer{})
	if e != nil {
		return fmt.Errorf("clients WireGuard invalides")
	}
	tun, network, e := netstack.CreateNetTUN([]netip.Addr{netip.MustParseAddr("10.77.0.1")}, nil, 1280)
	if e != nil {
		return fmt.Errorf("création du serveur WireGuard impossible")
	}
	dev := device.NewDevice(tun, conn.NewDefaultBind(), device.NewLogger(device.LogLevelSilent, ""))
	defer dev.Close()
	if dev.IpcSet(fmt.Sprintf("private_key=%s\nlisten_port=%d\n%s", private, cfg.ListenPort, commands)) != nil || dev.Up() != nil {
		return fmt.Errorf("port UDP indisponible ou serveur WireGuard impossible")
	}
	listener, e := network.ListenTCPAddrPort(netip.MustParseAddrPort("10.77.0.1:8766"))
	if e != nil {
		return fmt.Errorf("API virtuelle indisponible")
	}
	defer listener.Close()
	target, _ := url.Parse(fmt.Sprintf("http://127.0.0.1:%d", cfg.UpstreamPort))
	proxy := &httputil.ReverseProxy{FlushInterval: -1, ErrorLog: log.New(io.Discard, "", 0),
		Rewrite: func(r *httputil.ProxyRequest) {
			r.SetURL(target)
			r.Out.Header = http.Header{"Authorization": {r.In.Header.Get("Authorization")}, "Content-Type": {"application/json"}, "X-Qwen-Session": {r.In.Header.Get("X-Qwen-Session")}, "X-Qwen-Request": {r.In.Header.Get("X-Qwen-Request")}, "X-Fred-Agent-Protocol": {r.In.Header.Get("X-Fred-Agent-Protocol")}}
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, e error) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(503)
			io.WriteString(w, `{"error":{"code":"gateway_unavailable","message":"Passerelle IA locale indisponible."}}`)
		},
	}
	slots := make(chan struct{}, 32)
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Host != "10.77.0.1:8766" || r.Header.Get("Origin") != "" || r.URL.RawQuery != "" {
			http.Error(w, "Accès refusé", 403)
			return
		}
		if !((r.Method == "GET" && (r.URL.Path == "/v1/history" || r.URL.Path == "/v1/workspace" || r.URL.Path == "/v1/notifications" || r.URL.Path == "/v1/models" || r.URL.Path == "/v1/status" || r.URL.Path == "/v1/agent/state" || r.URL.Path == "/v1/voice/status" || r.URL.Path == "/v1/client/release" || r.URL.Path == "/v1/client/download" || r.URL.Path == "/v1/client/android/release" || r.URL.Path == "/v1/client/android/download")) || (r.Method == "POST" && (r.URL.Path == "/v1/embeddings" || r.URL.Path == "/v1/device" || r.URL.Path == "/v1/history" || r.URL.Path == "/v1/workspace/action" || r.URL.Path == "/v1/notifications/action" || r.URL.Path == "/v1/chat/completions" || r.URL.Path == "/v1/context" || r.URL.Path == "/v1/cancel" || r.URL.Path == "/v1/agent/action" || r.URL.Path == "/v1/voice/speech" || r.URL.Path == "/v1/voice/cancel"))) {
			http.NotFound(w, r)
			return
		}
		bodyLimit := int64(2 * 1024 * 1024)
		if r.URL.Path == "/v1/embeddings" || r.URL.Path == "/v1/notifications/action" {
			bodyLimit = 65536
		}
		if r.URL.Path == "/v1/device" {
			bodyLimit = 2048
		}
		if r.URL.Path == "/v1/workspace/action" {
			bodyLimit = 8 * 1024 * 1024
		}
		if r.URL.Path == "/v1/history" {
			bodyLimit = 10 * 1024 * 1024
		}
		if r.Method == "POST" && (r.ContentLength < 1 || r.ContentLength > bodyLimit) {
			http.Error(w, "Requête trop volumineuse", 413)
			return
		}
		select {
		case slots <- struct{}{}:
			defer func() { <-slots }()
		default:
			http.Error(w, "Serveur occupé", 429)
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, bodyLimit)
		proxy.ServeHTTP(w, r)
	})
	server := &http.Server{Handler: handler, ReadTimeout: 30 * time.Second, ReadHeaderTimeout: 5 * time.Second, MaxHeaderBytes: 16384}
	go func() {
		defer server.Close()
		for {
			var update struct {
				Peers []Peer `json:"peers"`
			}
			if decoder.Decode(&update) != nil {
				return
			}
			ipc, next, e := peerCommands(update.Peers, peers)
			if e != nil || dev.IpcSet(ipc) != nil {
				json.NewEncoder(os.Stdout).Encode(map[string]string{"error": "Mise à jour des clients impossible"})
				continue
			}
			peers = next
			json.NewEncoder(os.Stdout).Encode(map[string]bool{"peers_updated": true})
		}
	}()
	actual := cfg.ListenPort
	if dump, e := dev.IpcGet(); e == nil {
		for _, line := range strings.Split(dump, "\n") {
			if strings.HasPrefix(line, "listen_port=") {
				actual, _ = strconv.Atoi(strings.TrimPrefix(line, "listen_port="))
			}
		}
	}
	json.NewEncoder(os.Stdout).Encode(map[string]any{"ready": true, "role": "server", "udp_port": actual})
	e = server.Serve(listener)
	if e == http.ErrServerClosed {
		return nil
	}
	return e
}
func keyHex(value string) (string, error) {
	b, err := base64.StdEncoding.DecodeString(value)
	if err != nil || len(b) != 32 {
		return "", fmt.Errorf("clé invalide")
	}
	return hex.EncodeToString(b), nil
}
func validate(c Config) (string, error) {
	p, e := netip.ParsePrefix(c.WireGuard.Address)
	if e != nil || p.Bits() != 32 || !netip.MustParsePrefix("10.77.0.0/24").Contains(p.Addr()) || p.Addr() == netip.MustParseAddr("10.77.0.1") || p.Addr() == netip.MustParseAddr("10.77.0.0") || p.Addr() == netip.MustParseAddr("10.77.0.255") {
		return "", fmt.Errorf("adresse invalide")
	}
	host, port, e := net.SplitHostPort(c.WireGuard.Endpoint)
	number, pe := strconv.Atoi(port)
	if e != nil || pe != nil || host == "" || number < 1 || number > 65535 || strings.ContainsAny(host, "\r\n\t /\\") {
		return "", fmt.Errorf("adresse serveur invalide")
	}
	if len(c.APIToken) < 50 || len(c.BridgeToken) < 32 {
		return "", fmt.Errorf("accès invalide")
	}
	private, e := keyHex(c.WireGuard.PrivateKey)
	if e != nil {
		return "", e
	}
	public, e := keyHex(c.WireGuard.ServerPublicKey)
	if e != nil {
		return "", e
	}
	psk, e := keyHex(c.WireGuard.PresharedKey)
	if e != nil {
		return "", e
	}
	return fmt.Sprintf("private_key=%s\npublic_key=%s\npreshared_key=%s\nendpoint=%s\nallowed_ip=10.77.0.1/32\npersistent_keepalive_interval=25\n", private, public, psk, c.WireGuard.Endpoint), nil
}

func run() error {
	var cfg Config
	decoder := json.NewDecoder(os.Stdin)
	if decoder.Decode(&cfg) != nil {
		return fmt.Errorf("profil WireGuard illisible")
	}
	if cfg.Role == "server" {
		return runServer(cfg, decoder)
	}
	if cfg.Role != "" && cfg.Role != "client" {
		return fmt.Errorf("rôle WireGuard invalide")
	}
	ipc, err := validate(cfg)
	if err != nil {
		return fmt.Errorf("profil WireGuard invalide")
	}
	address := netip.MustParsePrefix(cfg.WireGuard.Address).Addr()
	tun, network, err := netstack.CreateNetTUN([]netip.Addr{address}, nil, 1280)
	if err != nil {
		return fmt.Errorf("création du tunnel impossible")
	}
	dev := device.NewDevice(tun, conn.NewDefaultBind(), device.NewLogger(device.LogLevelSilent, ""))
	defer dev.Close()
	if dev.IpcSet(ipc) != nil || dev.Up() != nil {
		return fmt.Errorf("activation du tunnel impossible")
	}
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return err
	}
	defer listener.Close()
	target, _ := url.Parse("http://10.77.0.1:8766")
	transport := &http.Transport{
		DialContext: func(ctx context.Context, kind, address string) (net.Conn, error) {
			ctx, cancel := context.WithTimeout(ctx, 20*time.Second)
			defer cancel()
			return network.DialContext(ctx, kind, address)
		},
		ResponseHeaderTimeout: 900 * time.Second, IdleConnTimeout: 20 * time.Second,
		MaxConnsPerHost: 4, DisableKeepAlives: true,
	}
	defer transport.CloseIdleConnections()
	proxy := &httputil.ReverseProxy{
		Transport: transport, FlushInterval: -1, ErrorLog: log.New(io.Discard, "", 0),
		Rewrite: func(r *httputil.ProxyRequest) {
			r.SetURL(target)
			r.Out.Header = http.Header{"Authorization": {"Bearer " + cfg.APIToken}, "Content-Type": {"application/json"}, "X-Qwen-Session": {r.In.Header.Get("X-Qwen-Session")}, "X-Qwen-Request": {r.In.Header.Get("X-Qwen-Request")}, "X-Fred-Agent-Protocol": {r.In.Header.Get("X-Fred-Agent-Protocol")}}
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, e error) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(503)
			code, message := "wireguard_unreachable", "Aucune réponse du serveur WireGuard. Vérifier l’adresse, le port UDP, le pare-feu et l’accès client."
			if dump, err := dev.IpcGet(); err == nil {
				for _, line := range strings.Split(dump, "\n") {
					if name, value, ok := strings.Cut(line, "="); ok && name == "last_handshake_time_sec" {
						if handshake, _ := strconv.ParseInt(value, 10, 64); handshake > 0 {
							code, message = "tunnel_request_failed", "WireGuard a établi le tunnel, mais cette requête a été interrompue. Vérifier les coupures réseau, la charge du serveur et l’utilisation d’un EXE distinct par PC."
						}
					}
				}
			}
			json.NewEncoder(w).Encode(map[string]any{"error": map[string]string{"code": code, "message": message}})
		},
	}
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Host != listener.Addr().String() || r.Header.Get("Origin") != "" || subtle.ConstantTimeCompare([]byte(r.Header.Get("X-Qwen-Bridge")), []byte(cfg.BridgeToken)) != 1 {
			http.Error(w, "Accès local refusé", 403)
			return
		}
		if r.Method == "GET" && r.URL.Path == "/bridge/status" && r.URL.RawQuery == "" {
			status := map[string]any{"handshake": false}
			if dump, e := dev.IpcGet(); e == nil {
				// Explicit whitelist: IpcGet also contains private keys and must never be returned.
				for _, line := range strings.Split(dump, "\n") {
					name, value, ok := strings.Cut(line, "=")
					if !ok {
						continue
					}
					if name == "endpoint" {
						status["resolved_endpoint"] = value
					}
					if name == "last_handshake_time_sec" || name == "rx_bytes" || name == "tx_bytes" {
						number, _ := strconv.ParseInt(value, 10, 64)
						status[name] = number
						if name == "last_handshake_time_sec" {
							status["handshake"] = number > 0
						}
					}
				}
			}
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("Cache-Control", "no-store")
			json.NewEncoder(w).Encode(status)
			return
		}
		if r.URL.RawQuery != "" || !((r.Method == "GET" && (r.URL.Path == "/v1/history" || r.URL.Path == "/v1/workspace" || r.URL.Path == "/v1/notifications" || r.URL.Path == "/v1/models" || r.URL.Path == "/v1/status" || r.URL.Path == "/v1/agent/state" || r.URL.Path == "/v1/voice/status" || r.URL.Path == "/v1/client/release" || r.URL.Path == "/v1/client/download" || r.URL.Path == "/v1/client/android/release" || r.URL.Path == "/v1/client/android/download")) || (r.Method == "POST" && (r.URL.Path == "/v1/embeddings" || r.URL.Path == "/v1/device" || r.URL.Path == "/v1/history" || r.URL.Path == "/v1/workspace/action" || r.URL.Path == "/v1/notifications/action" || r.URL.Path == "/v1/chat/completions" || r.URL.Path == "/v1/context" || r.URL.Path == "/v1/cancel" || r.URL.Path == "/v1/agent/action" || r.URL.Path == "/v1/voice/speech" || r.URL.Path == "/v1/voice/cancel"))) {
			http.NotFound(w, r)
			return
		}
		bodyLimit := int64(2 * 1024 * 1024)
		if r.URL.Path == "/v1/embeddings" || r.URL.Path == "/v1/notifications/action" {
			bodyLimit = 65536
		}
		if r.URL.Path == "/v1/device" {
			bodyLimit = 2048
		}
		if r.URL.Path == "/v1/workspace/action" {
			bodyLimit = 8 * 1024 * 1024
		}
		if r.URL.Path == "/v1/history" {
			bodyLimit = 10 * 1024 * 1024
		}
		if r.Method == "POST" && (r.ContentLength < 1 || r.ContentLength > bodyLimit) {
			http.Error(w, "Corps JSON trop volumineux", 413)
			return
		}
		if r.Method == "GET" && r.URL.Path != "/v1/client/download" && r.URL.Path != "/v1/client/android/download" {
			// Allow handshake retries on remote networks before declaring the tunnel unavailable.
			ctx, cancel := context.WithTimeout(r.Context(), 25*time.Second)
			defer cancel()
			r = r.WithContext(ctx)
		}
		r.Body = http.MaxBytesReader(w, r.Body, bodyLimit)
		proxy.ServeHTTP(w, r)
	})
	server := &http.Server{Handler: handler, ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 20 * time.Second, MaxHeaderBytes: 16384}
	go func() { io.Copy(io.Discard, os.Stdin); server.Close() }()
	if json.NewEncoder(os.Stdout).Encode(map[string]any{"ready": true, "port": listener.Addr().(*net.TCPAddr).Port}) != nil {
		return fmt.Errorf("parent client indisponible")
	}
	err = server.Serve(listener)
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}
func main() {
	if len(os.Args) == 2 && os.Args[1] == "--self-test" {
		fmt.Println("WireGuard intégré OK")
		return
	}
	if err := run(); err != nil {
		json.NewEncoder(os.Stdout).Encode(map[string]string{"error": err.Error()})
		os.Exit(1)
	}
}
