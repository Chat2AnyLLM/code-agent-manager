package providers_test

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"

	"github.com/chat2anyllm/code-agent-manager/internal/providers"
)

func ptr[T any](v T) *T { return &v }

func TestLoadOrInitMissingReturnsSkeleton(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "providers.json")

	file, created, err := loadOrInitLegacyFileForTest(path)
	if err != nil {
		t.Fatalf("LoadOrInit err = %v", err)
	}
	if !created {
		t.Fatal("expected created=true for missing file")
	}
	if file.Common == nil {
		t.Fatal("expected non-nil Common")
	}
	if file.Endpoints == nil {
		t.Fatal("expected non-nil Endpoints")
	}
	if len(file.Endpoints) != 0 {
		t.Fatalf("expected empty endpoints, got %d", len(file.Endpoints))
	}
	if _, err := os.Stat(path); !errors.Is(err, os.ErrNotExist) {
		t.Fatal("LoadOrInit must not write the file itself")
	}
}

func TestLoadOrInitExistingFile(t *testing.T) {
	path := writeRawProviders(t, `{"endpoints":{"a":{"endpoint":"https://a.example"}}}`)
	file, created, err := loadOrInitLegacyFileForTest(path)
	if err != nil {
		t.Fatalf("LoadOrInit err = %v", err)
	}
	if created {
		t.Fatal("expected created=false for existing file")
	}
	if _, ok := file.Endpoints["a"]; !ok {
		t.Fatal("expected endpoint 'a' to load")
	}
}

func TestLoadOrInitMalformedJSON(t *testing.T) {
	path := writeRawProviders(t, "not-json")
	if _, _, err := loadOrInitLegacyFileForTest(path); err == nil {
		t.Fatal("expected error on malformed JSON")
	}
}

func TestSaveRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "subdir", "providers.json")
	file := providers.File{
		Common: map[string]any{"http_proxy": "http://example:8080"},
		Endpoints: map[string]providers.Endpoint{
			"alpha": {
				Endpoint:        "https://alpha.example",
				APIKeyEnv:       "ALPHA",
				SupportedClient: "claude,codex",
				Models:          []string{"m1", "m2"},
			},
		},
	}
	if err := saveLegacyFileForTest(path, file); err != nil {
		t.Fatalf("Save err = %v", err)
	}

	got, err := loadLegacyStoreFileForTest(path)
	if err != nil {
		t.Fatalf("Load err = %v", err)
	}
	if !reflect.DeepEqual(got.Endpoints["alpha"].Models, []string{"m1", "m2"}) {
		t.Fatalf("models = %v", got.Endpoints["alpha"].Models)
	}
}

func TestSaveCreatesParentDirAndSetsPerm(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("permission bits not meaningful on windows")
	}
	dir := t.TempDir()
	path := filepath.Join(dir, "nested", "providers.json")
	if err := saveLegacyFileForTest(path, providers.File{}); err != nil {
		t.Fatalf("Save err = %v", err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat err = %v", err)
	}
	if perm := info.Mode().Perm(); perm != 0o600 {
		t.Fatalf("perm = %o, want 0600", perm)
	}
	dirInfo, err := os.Stat(filepath.Dir(path))
	if err != nil {
		t.Fatalf("stat dir err = %v", err)
	}
	if perm := dirInfo.Mode().Perm(); perm&0o077 != 0 {
		t.Fatalf("parent dir perm too open: %o", perm)
	}
}

func TestSaveNilMapsBecomeEmpty(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "providers.json")
	if err := saveLegacyFileForTest(path, providers.File{}); err != nil {
		t.Fatalf("Save err = %v", err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read err = %v", err)
	}
	parsed := map[string]any{}
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("parse err = %v", err)
	}
	if _, ok := parsed["common"]; !ok {
		t.Fatal("expected 'common' key to be present")
	}
	if _, ok := parsed["endpoints"]; !ok {
		t.Fatal("expected 'endpoints' key to be present")
	}
}

func TestAddHappyAndDuplicate(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{}}
	if err := providers.Add(&file, "alpha", providers.Endpoint{Endpoint: "https://a"}); err != nil {
		t.Fatalf("Add err = %v", err)
	}
	if file.Endpoints["alpha"].Endpoint != "https://a" {
		t.Fatal("expected alpha endpoint stored")
	}
	err := providers.Add(&file, "alpha", providers.Endpoint{})
	if !errors.Is(err, providers.ErrAlreadyExists) {
		t.Fatalf("Add duplicate err = %v, want ErrAlreadyExists", err)
	}
}

func TestAddRejectsInvalidName(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{}}
	if err := providers.Add(&file, "", providers.Endpoint{}); !errors.Is(err, providers.ErrInvalidName) {
		t.Fatalf("Add empty err = %v, want ErrInvalidName", err)
	}
	if err := providers.Add(&file, "has space", providers.Endpoint{}); !errors.Is(err, providers.ErrInvalidName) {
		t.Fatalf("Add space err = %v, want ErrInvalidName", err)
	}
}

func TestUpdateSparsePatch(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{
		"alpha": {Endpoint: "https://a", APIKeyEnv: "OLD", Description: "old"},
	}}
	patch := providers.Patch{
		APIKeyEnv:   ptr("NEW"),
		Description: ptr("brand new"),
	}
	if err := providers.Update(&file, "alpha", patch); err != nil {
		t.Fatalf("Update err = %v", err)
	}
	got := file.Endpoints["alpha"]
	if got.Endpoint != "https://a" {
		t.Fatalf("Endpoint changed unexpectedly: %q", got.Endpoint)
	}
	if got.APIKeyEnv != "NEW" {
		t.Fatalf("APIKeyEnv = %q, want NEW", got.APIKeyEnv)
	}
	if got.Description != "brand new" {
		t.Fatalf("Description = %q", got.Description)
	}
}

func TestUpdateListOpsForClients(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{
		"alpha": {SupportedClient: "claude,codex"},
	}}
	if err := providers.Update(&file, "alpha", providers.Patch{
		Clients: &providers.ListPatch{Op: providers.ListOpAdd, Items: []string{"droid"}},
	}); err != nil {
		t.Fatalf("add err = %v", err)
	}
	if got := file.Endpoints["alpha"].SupportedClient; got != "claude,codex,droid" {
		t.Fatalf("after add: %q", got)
	}
	if err := providers.Update(&file, "alpha", providers.Patch{
		Clients: &providers.ListPatch{Op: providers.ListOpRemove, Items: []string{"codex"}},
	}); err != nil {
		t.Fatalf("remove err = %v", err)
	}
	if got := file.Endpoints["alpha"].SupportedClient; got != "claude,droid" {
		t.Fatalf("after remove: %q", got)
	}
	if err := providers.Update(&file, "alpha", providers.Patch{
		Clients: &providers.ListPatch{Op: providers.ListOpReplace, Items: []string{"gemini"}},
	}); err != nil {
		t.Fatalf("replace err = %v", err)
	}
	if got := file.Endpoints["alpha"].SupportedClient; got != "gemini" {
		t.Fatalf("after replace: %q", got)
	}
}

func TestUpdateListOpsForModels(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{
		"alpha": {Models: []string{"a", "b"}},
	}}
	if err := providers.Update(&file, "alpha", providers.Patch{
		Models: &providers.ListPatch{Op: providers.ListOpAdd, Items: []string{"b", "c"}},
	}); err != nil {
		t.Fatalf("add err = %v", err)
	}
	if got := file.Endpoints["alpha"].Models; !reflect.DeepEqual(got, []string{"a", "b", "c"}) {
		t.Fatalf("models = %v, want [a b c]", got)
	}
}

func TestUpdateUnknownProvider(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{}}
	err := providers.Update(&file, "ghost", providers.Patch{Endpoint: ptr("x")})
	if !errors.Is(err, providers.ErrNotFound) {
		t.Fatalf("Update unknown err = %v, want ErrNotFound", err)
	}
}

func TestRemoveHappyAndMissing(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{"alpha": {}}}
	if ok := providers.Remove(&file, "alpha"); !ok {
		t.Fatal("expected Remove to report true for present key")
	}
	if _, exists := file.Endpoints["alpha"]; exists {
		t.Fatal("expected alpha to be deleted")
	}
	if ok := providers.Remove(&file, "ghost"); ok {
		t.Fatal("expected Remove to report false for missing key")
	}
}

func TestRenameHappy(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{
		"alpha": {Endpoint: "https://a"},
	}}
	if err := providers.Rename(&file, "alpha", "beta"); err != nil {
		t.Fatalf("Rename err = %v", err)
	}
	if _, ok := file.Endpoints["alpha"]; ok {
		t.Fatal("expected old key removed")
	}
	if got := file.Endpoints["beta"].Endpoint; got != "https://a" {
		t.Fatalf("beta endpoint = %q", got)
	}
}

func TestRenameSourceMissing(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{}}
	err := providers.Rename(&file, "alpha", "beta")
	if !errors.Is(err, providers.ErrNotFound) {
		t.Fatalf("err = %v, want ErrNotFound", err)
	}
}

func TestRenameDestExists(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{
		"alpha": {Endpoint: "https://a"},
		"beta":  {Endpoint: "https://b"},
	}}
	err := providers.Rename(&file, "alpha", "beta")
	if !errors.Is(err, providers.ErrAlreadyExists) {
		t.Fatalf("err = %v, want ErrAlreadyExists", err)
	}
}

func TestSetEnabledTogglesAndErrors(t *testing.T) {
	file := providers.File{Endpoints: map[string]providers.Endpoint{
		"alpha": {Endpoint: "https://a"},
	}}
	if err := providers.SetEnabled(&file, "alpha", false); err != nil {
		t.Fatalf("disable err = %v", err)
	}
	if file.Endpoints["alpha"].IsEnabled() {
		t.Fatal("expected alpha disabled")
	}
	if err := providers.SetEnabled(&file, "alpha", true); err != nil {
		t.Fatalf("enable err = %v", err)
	}
	if !file.Endpoints["alpha"].IsEnabled() {
		t.Fatal("expected alpha enabled")
	}
	if err := providers.SetEnabled(&file, "ghost", true); !errors.Is(err, providers.ErrNotFound) {
		t.Fatalf("err = %v, want ErrNotFound", err)
	}
}

func TestSaveThenLoadOrInitMatchesDiskFormat(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "providers.json")
	enabled := true
	file := providers.File{
		Common: map[string]any{"cache_ttl_seconds": float64(3600)},
		Endpoints: map[string]providers.Endpoint{
			"alpha": {
				Endpoint:        "https://a",
				SupportedClient: "claude",
				Models:          []string{"m1"},
				Enabled:         &enabled,
			},
		},
	}
	if err := saveLegacyFileForTest(path, file); err != nil {
		t.Fatal(err)
	}
	loaded, created, err := loadOrInitLegacyFileForTest(path)
	if err != nil {
		t.Fatal(err)
	}
	if created {
		t.Fatal("expected created=false after Save")
	}
	if !loaded.Endpoints["alpha"].IsEnabled() {
		t.Fatal("expected alpha enabled after round-trip")
	}
	if strings.TrimSpace(loaded.Endpoints["alpha"].SupportedClient) != "claude" {
		t.Fatalf("SupportedClient = %q", loaded.Endpoints["alpha"].SupportedClient)
	}
}

func writeRawProviders(t *testing.T, body string) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "providers.json")
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func loadLegacyStoreFileForTest(path string) (providers.File, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return providers.File{}, err
	}
	var file providers.File
	if err := json.Unmarshal(data, &file); err != nil {
		return providers.File{}, err
	}
	if file.Common == nil {
		file.Common = map[string]any{}
	}
	if file.Endpoints == nil {
		file.Endpoints = map[string]providers.Endpoint{}
	}
	return file, nil
}

func loadOrInitLegacyFileForTest(path string) (providers.File, bool, error) {
	if _, err := os.Stat(path); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return providers.File{Common: map[string]any{}, Endpoints: map[string]providers.Endpoint{}}, true, nil
		}
		return providers.File{}, false, err
	}
	file, err := loadLegacyStoreFileForTest(path)
	if err != nil {
		return providers.File{}, false, err
	}
	return file, false, nil
}

func saveLegacyFileForTest(path string, file providers.File) error {
	if file.Common == nil {
		file.Common = map[string]any{}
	}
	if file.Endpoints == nil {
		file.Endpoints = map[string]providers.Endpoint{}
	}
	dir := filepath.Dir(path)
	if dir != "" {
		if err := os.MkdirAll(dir, 0o700); err != nil {
			return err
		}
	}
	data, err := json.MarshalIndent(file, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0o600)
}
