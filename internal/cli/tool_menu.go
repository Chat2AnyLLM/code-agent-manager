package cli

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// pickerStep is the reusable filterable-list component shared by the
// tool-only menu (toolMenuModel) and the multi-phase launch wizard.
// It holds presentation state — title, items, filter, cursor — and
// reacts to key events via Update. It is NOT a tea.Model by itself;
// the wrapping model decides when to quit / advance / step back.
type pickerStep struct {
	title        string
	items        []string
	cursor       int
	filter       string
	visibleLimit int
	// hint is the footer line shown beneath the list.
	hint string
}

func newPickerStep(title string, items []string, hint string) pickerStep {
	return newLimitedPickerStep(title, items, hint, 0)
}

func newLimitedPickerStep(title string, items []string, hint string, limit int) pickerStep {
	return pickerStep{
		title:        title,
		items:        append([]string(nil), items...),
		visibleLimit: limit,
		hint:         hint,
	}
}

// pickerAction summarises what the wrapping model should do after a
// key event.
type pickerAction int

const (
	pickerActionNone    pickerAction = iota
	pickerActionAdvance              // Enter pressed on a non-empty filtered list
	pickerActionBack                 // Esc pressed
	pickerActionAbort                // q or Ctrl+C pressed
)

// update mutates the step in place and reports the high-level action.
// Returns pickerActionNone for filter/movement keys.
func (s *pickerStep) update(msg tea.KeyMsg) pickerAction {
	switch msg.String() {
	case "ctrl+c", "q":
		return pickerActionAbort
	case "esc":
		return pickerActionBack
	case "up", "k":
		if s.cursor > 0 {
			s.cursor--
		}
	case "down", "j":
		if s.cursor < len(s.filtered())-1 {
			s.cursor++
		}
	case "enter":
		if len(s.filtered()) > 0 {
			return pickerActionAdvance
		}
	case "backspace":
		if s.filter != "" {
			s.filter = s.filter[:len(s.filter)-1]
			s.clampCursor()
		}
	default:
		text := msg.String()
		if len(text) == 1 && text != "/" {
			s.filter += text
			s.clampCursor()
		}
	}
	return pickerActionNone
}

// selected returns the currently highlighted item, or "" when the
// filtered list is empty.
func (s pickerStep) selected() string {
	v := s.filtered()
	if len(v) == 0 {
		return ""
	}
	return v[s.cursor]
}

func (s pickerStep) view() string {
	var b strings.Builder
	b.WriteString(s.title)
	b.WriteString("\n\n")
	if s.filter != "" {
		fmt.Fprintf(&b, "Filter: %s\n\n", s.filter)
	}
	v, offset := s.visibleWindow()
	if len(v) == 0 {
		b.WriteString("No items match your filter.\n")
	} else {
		for i, item := range v {
			cursor := " "
			if i+offset == s.cursor {
				cursor = ">"
			}
			fmt.Fprintf(&b, "%s %s\n", cursor, item)
		}
	}
	if s.hint != "" {
		b.WriteString("\n")
		b.WriteString(s.hint)
		b.WriteString("\n")
	}
	return b.String()
}

func (s pickerStep) visible() []string {
	v, _ := s.visibleWindow()
	return v
}

func (s pickerStep) visibleWindow() ([]string, int) {
	out := s.filtered()
	if s.visibleLimit <= 0 || len(out) <= s.visibleLimit {
		return out, 0
	}
	start := s.cursor - s.visibleLimit + 1
	if start < 0 {
		start = 0
	}
	end := start + s.visibleLimit
	if end > len(out) {
		end = len(out)
	}
	return out[start:end], start
}

func (s pickerStep) filtered() []string {
	if s.filter == "" {
		return s.items
	}
	out := make([]string, 0, len(s.items))
	filter := strings.ToLower(s.filter)
	for _, item := range s.items {
		if strings.Contains(strings.ToLower(item), filter) {
			out = append(out, item)
		}
	}
	return out
}

func (s *pickerStep) clampCursor() {
	v := s.filtered()
	if len(v) == 0 {
		s.cursor = 0
		return
	}
	if s.cursor >= len(v) {
		s.cursor = len(v) - 1
	}
}

// toolMenuModel is the single-step tool picker. It now wraps a
// pickerStep so the wizard can share the underlying list rendering.
type toolMenuModel struct {
	step     pickerStep
	selected string
	quitting bool
}

func newToolMenuModel(tools []string) toolMenuModel {
	return toolMenuModel{
		step: newPickerStep(
			"Manage tools",
			tools,
			"Use ↑/↓ or j/k to move, type to filter, Enter to select, q to quit.",
		),
	}
}

func (m toolMenuModel) Init() tea.Cmd { return nil }

func (m toolMenuModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	key, ok := msg.(tea.KeyMsg)
	if !ok {
		return m, nil
	}
	switch m.step.update(key) {
	case pickerActionAbort, pickerActionBack:
		m.quitting = true
		return m, tea.Quit
	case pickerActionAdvance:
		m.selected = m.step.selected()
		return m, tea.Quit
	}
	return m, nil
}

func (m toolMenuModel) View() string {
	return m.step.view()
}
