package cli

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// multiSelectItem is one option in the multi-select list.
type multiSelectItem struct {
	label       string // display text
	description string // optional secondary line
	selected    bool
}

// multiSelectModel is a bubbletea model for picking one or more items
// from a filterable list.  It supports space to toggle, enter to confirm,
// arrow keys / j/k to move, type-to-filter, and 'a' to select all.
type multiSelectModel struct {
	title    string
	items    []multiSelectItem
	cursor   int
	filter   string
	done     bool
	aborted  bool
}

func newMultiSelectModel(title string, items []multiSelectItem) multiSelectModel {
	return multiSelectModel{
		title: title,
		items: items,
	}
}

func (m multiSelectModel) Init() tea.Cmd { return nil }

func (m multiSelectModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	key, ok := msg.(tea.KeyMsg)
	if !ok {
		return m, nil
	}
	vis := m.visible()
	switch key.String() {
	case "ctrl+c", "q":
		m.aborted = true
		return m, tea.Quit
	case "esc":
		m.aborted = true
		return m, tea.Quit
	case "up", "k":
		if m.cursor > 0 {
			m.cursor--
		}
	case "down", "j":
		if m.cursor < len(vis)-1 {
			m.cursor++
		}
	case " ": // toggle — cursor stays on the selected row
		if len(vis) > 0 {
			idx := m.realIndex(vis[m.cursor].label)
			if idx >= 0 {
				m.items[idx].selected = !m.items[idx].selected
			}
		}
	case "right": // select all visible
		for i := range m.items {
			m.items[i].selected = true
		}
	case "left": // deselect all
		for i := range m.items {
			m.items[i].selected = false
		}
	case "enter":
		m.done = true
		return m, tea.Quit
	case "backspace":
		if m.filter != "" {
			m.filter = m.filter[:len(m.filter)-1]
			m.clampCursor()
		}
	default:
		text := key.String()
		if len(text) == 1 && text != "/" {
			m.filter += text
			m.clampCursor()
		}
	}
	return m, nil
}

func (m multiSelectModel) View() string {
	var b strings.Builder
	b.WriteString(m.title)
	b.WriteString("\n\n")

	if m.filter != "" {
		fmt.Fprintf(&b, "Filter: %s\n\n", m.filter)
	}

	vis := m.visible()
	if len(vis) == 0 {
		b.WriteString("No items match your filter.\n")
	} else {
		for i, item := range vis {
			cursor := " "
			if i == m.cursor {
				cursor = ">"
			}
			check := "[ ]"
			if item.selected {
				check = "[x]"
			}
			fmt.Fprintf(&b, "%s %s  %s\n", cursor, check, item.label)
			if item.description != "" {
				// Indent description to align under the label text.
				fmt.Fprintf(&b, "        %s\n", item.description)
			}
		}
	}

	count := m.selectedCount()
	b.WriteString("\n")
	fmt.Fprintf(&b, "%d selected · space=toggle · ←all off · →all on · enter=confirm · type to filter · q=quit\n", count)
	return b.String()
}

func (m multiSelectModel) visible() []multiSelectItem {
	if m.filter == "" {
		return m.items
	}
	filter := strings.ToLower(m.filter)
	var out []multiSelectItem
	for _, item := range m.items {
		if strings.Contains(strings.ToLower(item.label), filter) ||
			strings.Contains(strings.ToLower(item.description), filter) {
			out = append(out, item)
		}
	}
	return out
}

func (m *multiSelectModel) clampCursor() {
	vis := m.visible()
	if len(vis) == 0 {
		m.cursor = 0
		return
	}
	if m.cursor >= len(vis) {
		m.cursor = len(vis) - 1
	}
}

func (m multiSelectModel) realIndex(label string) int {
	for i, item := range m.items {
		if item.label == label {
			return i
		}
	}
	return -1
}

func (m multiSelectModel) selectedCount() int {
	n := 0
	for _, item := range m.items {
		if item.selected {
			n++
		}
	}
	return n
}

func (m multiSelectModel) selectedLabels() []string {
	var out []string
	for _, item := range m.items {
		if item.selected {
			out = append(out, item.label)
		}
	}
	return out
}

// runMultiSelect runs a bubbletea multi-select picker and returns the
// selected labels.  Returns nil if the user aborted.
func runMultiSelect(title string, items []multiSelectItem) ([]string, error) {
	model := newMultiSelectModel(title, items)
	p := tea.NewProgram(model)
	final, err := p.Run()
	if err != nil {
		return nil, err
	}
	result := final.(multiSelectModel)
	if result.aborted {
		return nil, nil
	}
	return result.selectedLabels(), nil
}
