package cli

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

const defaultPageSize = 15

// multiSelectItem is one option in the multi-select list.
type multiSelectItem struct {
	label       string // display text
	description string // optional secondary line
	selected    bool
}

// multiSelectModel is a bubbletea model for picking one or more items
// from a filterable, scrollable list.  Supports space to toggle, enter
// to confirm, arrow keys / j/k to move, type-to-filter, and ←/→ for
// select-all / deselect-all.  Only a window of pageSize items is shown;
// the view scrolls as the cursor moves.
type multiSelectModel struct {
	title    string
	items    []multiSelectItem
	cursor   int
	offset   int // first visible row index (scroll offset)
	pageSize int
	filter   string
	done     bool
	aborted  bool
}

func newMultiSelectModel(title string, items []multiSelectItem) multiSelectModel {
	return multiSelectModel{
		title:    title,
		items:    items,
		pageSize: defaultPageSize,
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
			m.scrollToCursor(vis)
		}
	case "down", "j":
		if m.cursor < len(vis)-1 {
			m.cursor++
			m.scrollToCursor(vis)
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
		// Compute the visible window.
		end := m.offset + m.pageSize
		if end > len(vis) {
			end = len(vis)
		}

		// Show scroll-up indicator.
		if m.offset > 0 {
			fmt.Fprintf(&b, "  ↑ %d more above\n", m.offset)
		}

		for i := m.offset; i < end; i++ {
			item := vis[i]
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
				fmt.Fprintf(&b, "        %s\n", item.description)
			}
		}

		// Show scroll-down indicator.
		remaining := len(vis) - end
		if remaining > 0 {
			fmt.Fprintf(&b, "  ↓ %d more below\n", remaining)
		}
	}

	count := m.selectedCount()
	b.WriteString("\n")
	fmt.Fprintf(&b, "%d selected · space=toggle · ←all off · →all on · enter=confirm · type to filter · q=quit\n", count)
	return b.String()
}

// scrollToCursor adjusts the scroll offset so the cursor is visible.
func (m *multiSelectModel) scrollToCursor(vis []multiSelectItem) {
	if len(vis) <= m.pageSize {
		m.offset = 0
		return
	}
	// Scroll up if cursor is above the window.
	if m.cursor < m.offset {
		m.offset = m.cursor
	}
	// Scroll down if cursor is below the window.
	if m.cursor >= m.offset+m.pageSize {
		m.offset = m.cursor - m.pageSize + 1
	}
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
		m.offset = 0
		return
	}
	if m.cursor >= len(vis) {
		m.cursor = len(vis) - 1
	}
	m.scrollToCursor(vis)
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
