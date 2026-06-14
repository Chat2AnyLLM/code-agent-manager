package main

import (
	"os"

	"github.com/chat2anyllm/code-agent-manager/internal/cli"
)

var version = "dev"

func main() {
	app := cli.New(cli.Options{Version: version, Stdout: os.Stdout, Stderr: os.Stderr})
	os.Exit(app.Run(os.Args[1:]))
}
