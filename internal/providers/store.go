// Package providers — write layer.
//
// store.go adds the mutation primitives (LoadOrInit, Save, Add, Update,
// Remove, Rename, SetEnabled) used by the `cam provider` CLI subcommands.
// The functions are intentionally pure: callers pass in an explicit path
// (or use providers.DiscoverPath) so the package never reaches into the
// filesystem on its own behalf.
package providers

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ListOp identifies how a list-valued patch should be combined with the
// existing slice on the endpoint being updated.
type ListOp int

const (
	// ListOpReplace overwrites the existing slice with the patch value.
	ListOpReplace ListOp = iota
	// ListOpAdd appends the patch value, de-duplicating against existing
	// entries while preserving original order.
	ListOpAdd
	// ListOpRemove deletes patch entries from the existing slice.
	ListOpRemove
)

// ListPatch carries a list-valued change for Update. A nil *ListPatch means
// "leave the field alone".
type ListPatch struct {
	Op    ListOp
	Items []string
}

// Patch is a sparse update payload. Nil-valued fields are left untouched on
// the target endpoint. Pointer-to-string is used (rather than a bare string)
// so callers can distinguish "set to empty" from "do not touch".
type Patch struct {
	Endpoint        *string
	APIKey          *string
	APIKeyEnv       *string
	Description     *string
	ListModelsCmd   *string
	KeepProxyConfig *bool
	UseProxy        *bool
	Enabled         *bool
	Clients         *ListPatch
	Models          *ListPatch
}

// LoadOrInit returns the parsed providers.json at path. If the file does
// not exist, an empty File{Common:{}, Endpoints:{}} is returned with
// created=true so the caller can report "creating new file" semantics on
// the first save. Malformed JSON surfaces a descriptive error.
func LoadOrInit(path string) (File, bool, error) {
	if path == "" {
		path = DefaultPath()
	}
	if _, err := os.Stat(path); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return File{
				Common:    map[string]any{},
				Endpoints: map[string]Endpoint{},
			}, true, nil
		}
		return File{}, false, fmt.Errorf("providers: stat %s: %w", path, err)
	}
	file, err := Load(path)
	if err != nil {
		return File{}, false, err
	}
	if file.Common == nil {
		file.Common = map[string]any{}
	}
	if file.Endpoints == nil {
		file.Endpoints = map[string]Endpoint{}
	}
	return file, false, nil
}

// Save writes file to path atomically with mode 0o600 and 2-space JSON
// indentation. The parent directory is created with 0o700 if missing.
func Save(path string, file File) error {
	if path == "" {
		path = DefaultPath()
	}
	if file.Common == nil {
		file.Common = map[string]any{}
	}
	if file.Endpoints == nil {
		file.Endpoints = map[string]Endpoint{}
	}
	dir := filepath.Dir(path)
	if dir != "" {
		if err := os.MkdirAll(dir, 0o700); err != nil {
			return fmt.Errorf("providers: mkdir %s: %w", dir, err)
		}
	}
	data, err := json.MarshalIndent(file, "", "  ")
	if err != nil {
		return fmt.Errorf("providers: marshal: %w", err)
	}
	data = append(data, '\n')
	tmp, err := os.CreateTemp(dir, ".providers-*.json.tmp")
	if err != nil {
		return fmt.Errorf("providers: temp file: %w", err)
	}
	tmpPath := tmp.Name()
	cleanup := func() { _ = os.Remove(tmpPath) }
	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		cleanup()
		return fmt.Errorf("providers: write temp: %w", err)
	}
	if err := tmp.Chmod(0o600); err != nil {
		_ = tmp.Close()
		cleanup()
		return fmt.Errorf("providers: chmod temp: %w", err)
	}
	if err := tmp.Close(); err != nil {
		cleanup()
		return fmt.Errorf("providers: close temp: %w", err)
	}
	if err := os.Rename(tmpPath, path); err != nil {
		cleanup()
		return fmt.Errorf("providers: rename %s -> %s: %w", tmpPath, path, err)
	}
	return nil
}

// Add inserts ep under name. Returns ErrAlreadyExists if name is already
// present, so callers can give a user-friendly "already exists" message
// without string-matching the wrapped error.
func Add(file *File, name string, ep Endpoint) error {
	if file == nil {
		return errors.New("providers: nil file")
	}
	if err := validateName(name); err != nil {
		return err
	}
	if file.Endpoints == nil {
		file.Endpoints = map[string]Endpoint{}
	}
	if _, ok := file.Endpoints[name]; ok {
		return fmt.Errorf("provider %q already exists: %w", name, ErrAlreadyExists)
	}
	file.Endpoints[name] = ep
	return nil
}

// Update applies the sparse patch to the endpoint named name. Returns
// ErrNotFound if no such endpoint exists.
func Update(file *File, name string, patch Patch) error {
	if file == nil {
		return errors.New("providers: nil file")
	}
	ep, ok := file.Endpoints[name]
	if !ok {
		return fmt.Errorf("provider %q not found: %w", name, ErrNotFound)
	}
	if patch.Endpoint != nil {
		ep.Endpoint = *patch.Endpoint
	}
	if patch.APIKey != nil {
		ep.APIKey = *patch.APIKey
	}
	if patch.APIKeyEnv != nil {
		ep.APIKeyEnv = *patch.APIKeyEnv
	}
	if patch.Description != nil {
		ep.Description = *patch.Description
	}
	if patch.ListModelsCmd != nil {
		ep.ListModelsCmd = *patch.ListModelsCmd
	}
	if patch.KeepProxyConfig != nil {
		ep.KeepProxyConfig = *patch.KeepProxyConfig
	}
	if patch.UseProxy != nil {
		ep.UseProxy = *patch.UseProxy
	}
	if patch.Enabled != nil {
		v := *patch.Enabled
		ep.Enabled = &v
	}
	if patch.Clients != nil {
		current := ep.Clients()
		updated := applyListPatch(current, *patch.Clients)
		ep.SupportedClient = strings.Join(updated, ",")
	}
	if patch.Models != nil {
		ep.Models = applyListPatch(ep.Models, *patch.Models)
	}
	file.Endpoints[name] = ep
	return nil
}

// Remove deletes the endpoint named name. Returns false when no entry by
// that name existed.
func Remove(file *File, name string) bool {
	if file == nil || file.Endpoints == nil {
		return false
	}
	if _, ok := file.Endpoints[name]; !ok {
		return false
	}
	delete(file.Endpoints, name)
	return true
}

// Rename moves an endpoint key from oldName to newName. Errors when source
// is missing or destination already exists, so the caller never accidentally
// overwrites a different provider.
func Rename(file *File, oldName, newName string) error {
	if file == nil {
		return errors.New("providers: nil file")
	}
	if err := validateName(newName); err != nil {
		return err
	}
	ep, ok := file.Endpoints[oldName]
	if !ok {
		return fmt.Errorf("provider %q not found: %w", oldName, ErrNotFound)
	}
	if oldName == newName {
		return nil
	}
	if _, exists := file.Endpoints[newName]; exists {
		return fmt.Errorf("provider %q already exists: %w", newName, ErrAlreadyExists)
	}
	delete(file.Endpoints, oldName)
	file.Endpoints[newName] = ep
	return nil
}

// SetEnabled toggles the Enabled field on the named endpoint. Returns
// ErrNotFound if no such endpoint exists.
func SetEnabled(file *File, name string, enabled bool) error {
	if file == nil {
		return errors.New("providers: nil file")
	}
	ep, ok := file.Endpoints[name]
	if !ok {
		return fmt.Errorf("provider %q not found: %w", name, ErrNotFound)
	}
	v := enabled
	ep.Enabled = &v
	file.Endpoints[name] = ep
	return nil
}

// ErrAlreadyExists is returned by Add and Rename when the destination key
// is already taken.  Use errors.Is(err, ErrAlreadyExists) to detect it.
var ErrAlreadyExists = errors.New("provider already exists")

// ErrNotFound is returned by Update, Rename, SetEnabled when the target
// endpoint is missing. Use errors.Is(err, ErrNotFound) to detect it.
var ErrNotFound = errors.New("provider not found")

// ErrInvalidName is returned when an endpoint name contains characters
// that would break JSON keys or shell usage (whitespace).
var ErrInvalidName = errors.New("invalid provider name")

// validateName rejects empty names and names containing whitespace. JSON
// itself permits arbitrary key strings, but whitespace would make the
// provider unusable from the shell flag parser.
func validateName(name string) error {
	if name == "" {
		return fmt.Errorf("empty name: %w", ErrInvalidName)
	}
	for _, r := range name {
		if r == ' ' || r == '\t' || r == '\n' || r == '\r' {
			return fmt.Errorf("name %q contains whitespace: %w", name, ErrInvalidName)
		}
	}
	return nil
}

// applyListPatch combines current with patch according to patch.Op.
// The function preserves input order and de-duplicates results so a
// repeated `--client +droid` invocation is idempotent.
func applyListPatch(current []string, patch ListPatch) []string {
	switch patch.Op {
	case ListOpReplace:
		return dedupeKeepOrder(patch.Items)
	case ListOpAdd:
		merged := append([]string{}, current...)
		merged = append(merged, patch.Items...)
		return dedupeKeepOrder(merged)
	case ListOpRemove:
		remove := map[string]struct{}{}
		for _, item := range patch.Items {
			remove[item] = struct{}{}
		}
		out := make([]string, 0, len(current))
		for _, item := range current {
			if _, drop := remove[item]; drop {
				continue
			}
			out = append(out, item)
		}
		return out
	}
	return current
}

func dedupeKeepOrder(items []string) []string {
	seen := map[string]struct{}{}
	out := make([]string, 0, len(items))
	for _, item := range items {
		trimmed := strings.TrimSpace(item)
		if trimmed == "" {
			continue
		}
		if _, ok := seen[trimmed]; ok {
			continue
		}
		seen[trimmed] = struct{}{}
		out = append(out, trimmed)
	}
	return out
}
