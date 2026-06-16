package cli

import (
	"strings"
	"testing"
)

func TestMultiSelectViewShowsSkillInstallHint(t *testing.T) {
	model := newMultiSelectModel("Select skill(s) to install:", []multiSelectItem{
		{label: "qodo-skills", description: "Qodo skills"},
	})

	view := model.View()
	want := "Use arrows to move, space to select, <right> to all, <left> to none, type to filter"
	if !strings.Contains(view, want) {
		t.Fatalf("view missing hint %q:\n%s", want, view)
	}
}
