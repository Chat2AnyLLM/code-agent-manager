package desktop

import "testing"

func TestMCPServiceClientsAndRegistry(t *testing.T) {
	service := NewMCPService()
	clients := service.ListClients()
	if len(clients) == 0 {
		t.Fatal("expected supported clients")
	}

	matches, err := service.SearchRegistry("github")
	if err != nil {
		t.Fatalf("search registry: %v", err)
	}
	if matches == nil {
		t.Fatal("expected non-nil registry result slice")
	}
}

func TestMCPServiceListRegistry(t *testing.T) {
	service := NewMCPService()

	// Empty query lists the whole catalog; each item carries its install type.
	items, err := service.ListRegistry("", "user")
	if err != nil {
		t.Fatalf("list registry: %v", err)
	}
	if len(items) == 0 {
		t.Fatal("expected discovered registry servers")
	}
	var seen bool
	for _, item := range items {
		if item.Name != "" && item.InstallType != "" {
			seen = true
		}
	}
	if !seen {
		t.Fatalf("expected items with name + installType, got %+v", items[:min(3, len(items))])
	}

	// A query narrows the results to matches.
	filtered, err := service.ListRegistry("github", "user")
	if err != nil {
		t.Fatalf("list registry filtered: %v", err)
	}
	if len(filtered) >= len(items) {
		t.Fatalf("expected query to narrow results, got %d (all=%d)", len(filtered), len(items))
	}
	for _, item := range filtered {
		if item.Name == "" {
			t.Fatalf("expected named item, got %+v", item)
		}
	}
}

func TestMCPServiceInstallFromRegistry(t *testing.T) {
	service := NewMCPService()
	// Installing an unknown server fails fast without touching config.
	if _, err := service.InstallFromRegistry("claude", "user", "does-not-exist-mcp"); err == nil {
		t.Fatal("expected error installing unknown server")
	}
}

