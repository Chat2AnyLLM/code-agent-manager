package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/chat2anyllm/code-agent-manager/internal/sidecar"
)

var version = "dev"

func main() {
	host := flag.String("host", "127.0.0.1", "Host to bind")
	port := flag.Int("port", 0, "Port to bind; 0 selects a random free port")
	token := flag.String("token", "", "Bearer token required by API requests; random when empty")
	providersPath := flag.String("providers", "", "Deprecated: path to a legacy providers.json used only for one-time migration into the SQLite store")
	versionJSON := flag.Bool("version-json", false, "Print version JSON and exit")
	flag.Parse()

	if *versionJSON {
		_ = json.NewEncoder(os.Stdout).Encode(map[string]string{"version": version})
		return
	}

	if *token == "" {
		generated, err := randomToken()
		if err != nil {
			log.Fatalf("generate token: %v", err)
		}
		*token = generated
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	server := sidecar.New(sidecar.Options{Version: version, ProvidersPath: *providersPath, Token: *token})
	startup, err := server.ListenAndServe(ctx, *host, *port)
	if err != nil {
		log.Fatal(err)
	}
	if err := json.NewEncoder(os.Stdout).Encode(startup); err != nil {
		log.Fatal(err)
	}
	<-ctx.Done()
}

func randomToken() (string, error) {
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		return "", fmt.Errorf("read random bytes: %w", err)
	}
	return hex.EncodeToString(buf), nil
}
