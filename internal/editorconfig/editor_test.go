package editorconfig

import "testing"

func TestDefaultRegistryUnknownFormatReturnsError(t *testing.T) {
	original := defaultSpecs
	defaultSpecs = []spec{{name: "broken", format: Format("unknown")}}
	t.Cleanup(func() { defaultSpecs = original })
	if _, err := DefaultRegistry(); err == nil {
		t.Fatal("expected error for unknown format")
	}
}
