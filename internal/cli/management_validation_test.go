package cli

import (
	"testing"
)

// ============================================================================
// isValidSkillName tests
// ============================================================================

func TestIsValidSkillName(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"simple lowercase", "terraform", true},
		{"with hyphens", "code-review", true},
		{"with numbers", "skill123", true},
		{"uppercase", "MySkill", true},
		{"with underscore", "my_skill", true},
		{"with dot", "my.skill", true},
		{"empty string", "", false},
		{"too long", string(make([]byte, 65)), false},
		{"with slash", "path/skill", false},
		{"path traversal", "..", false},
		{"starts with dot", ".hidden", false},
		{"starts with hyphen", "-skill", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isValidSkillName(tt.input)
			if got != tt.expected {
				t.Errorf("isValidSkillName(%q) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}

func TestIsSpecCompliantName(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"lowercase with hyphens", "my-skill", true},
		{"all lowercase", "terraform", true},
		{"with numbers", "skill123", true},
		{"single char", "a", true},
		{"uppercase fails", "MySkill", false},
		{"underscore fails", "my_skill", false},
		{"consecutive hyphens fails", "my--skill", false},
		{"leading hyphen fails", "-skill", false},
		{"trailing hyphen fails", "skill-", false},
		{"empty", "", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isSpecCompliantName(tt.input)
			if got != tt.expected {
				t.Errorf("isSpecCompliantName(%q) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}

// ============================================================================
// isValidSkillPath tests
// ============================================================================

func TestIsValidSkillPath(t *testing.T) {
	tests := []struct {
		name     string
		path     string
		expected bool
	}{
		// Standard flat: skills/name/SKILL.md
		{"standard flat", "skills/terraform/SKILL.md", true},
		// Namespaced: skills/scope/name/SKILL.md
		{"namespaced", "skills/author/terraform/SKILL.md", true},
		// Deeply nested: prefix/skills/name/SKILL.md
		{"deeply nested", "prefix/skills/terraform/SKILL.md", true},
		// Deeply nested namespaced
		{"deeply nested namespaced", "prefix/skills/author/terraform/SKILL.md", true},
		// Root-level: name/SKILL.md
		{"root level", "terraform/SKILL.md", true},
		// Hidden segments rejected
		{"hidden dir rejected", ".claude/skills/terraform/SKILL.md", false},
		{"hidden parent", "prefix/.hidden/skills/terraform/SKILL.md", false},
		// Wrong manifest
		{"wrong manifest", "skills/terraform/AGENT.md", false},
		// Too short
		{"just SKILL.md", "SKILL.md", false},
		// Skills dir itself
		{"skills dir itself", "skills/SKILL.md", false},
		// Plugins dir itself rejected
		{"plugins dir", "plugins/SKILL.md", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isValidSkillPath(tt.path)
			if got != tt.expected {
				t.Errorf("isValidSkillPath(%q) = %v, want %v", tt.path, got, tt.expected)
			}
		})
	}
}

// ============================================================================
// isValidSkillFrontmatter tests
// ============================================================================

func TestIsValidSkillFrontmatter(t *testing.T) {
	tests := []struct {
		name     string
		content  string
		expected bool
	}{
		{
			"valid frontmatter",
			"---\nname: my-skill\ndescription: A useful skill\n---\n\nBody here.",
			true,
		},
		{
			"valid with quotes",
			"---\nname: \"my-skill\"\ndescription: \"A useful skill\"\n---\n",
			true,
		},
		{
			"missing name",
			"---\ndescription: A useful skill\n---\n",
			false,
		},
		{
			"missing description",
			"---\nname: my-skill\n---\n",
			false,
		},
		{
			"no frontmatter",
			"Just plain body text.",
			false,
		},
		{
			"empty name value",
			"---\nname:\ndescription: A useful skill\n---\n",
			false,
		},
		{
			"empty description value",
			"---\nname: my-skill\ndescription:\n---\n",
			false,
		},
		{
			"no closing delimiter still valid",
			"---\nname: my-skill\ndescription: A useful skill\n",
			true,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isValidSkillFrontmatter(tt.content)
			if got != tt.expected {
				t.Errorf("isValidSkillFrontmatter() = %v, want %v\ncontent: %q", got, tt.expected, tt.content)
			}
		})
	}
}

// ============================================================================
// isValidSkillResult tests
// ============================================================================

func TestIsValidSkillResult(t *testing.T) {
	tests := []struct {
		name      string
		path      string
		skillName string
		expected  bool
	}{
		{"valid standard", "skills/terraform/SKILL.md", "terraform", true},
		{"valid root level", "terraform/SKILL.md", "terraform", true},
		{"invalid name", "skills/../SKILL.md", "..", false},
		{"empty name", "skills//SKILL.md", "", false},
		{"hidden path", ".claude/skills/terraform/SKILL.md", "terraform", false},
		{"empty path valid name", "", "terraform", true}, // path is optional
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isValidSkillResult(tt.path, tt.skillName)
			if got != tt.expected {
				t.Errorf("isValidSkillResult(%q, %q) = %v, want %v", tt.path, tt.skillName, got, tt.expected)
			}
		})
	}
}

// ============================================================================
// relevanceScore tests
// ============================================================================

func TestRelevanceScore(t *testing.T) {
	tests := []struct {
		name  string
		sName string
		desc  string
		repo  string
		stars int
		query string
	}{
		{"exact match", "terraform", "", "", 0, "terraform"},
		{"partial match", "terraform-aws", "", "", 0, "terraform"},
		{"description match", "my-skill", "terraform infrastructure", "", 0, "terraform"},
		{"stars bonus", "terraform", "", "", 6000, "terraform"},
		{"no match", "unrelated", "nothing", "", 0, "terraform"},
	}

	// Exact match should score highest.
	exactScore := relevanceScore("terraform", "", "", 0, "terraform")
	partialScore := relevanceScore("terraform-aws", "", "", 0, "terraform")
	descScore := relevanceScore("my-skill", "terraform infrastructure", "", 0, "terraform")
	noMatchScore := relevanceScore("unrelated", "nothing", "", 0, "terraform")

	if exactScore <= partialScore {
		t.Errorf("exact match (%d) should score higher than partial (%d)", exactScore, partialScore)
	}
	if partialScore <= descScore {
		t.Errorf("partial name match (%d) should score higher than desc only (%d)", partialScore, descScore)
	}
	if descScore <= noMatchScore {
		t.Errorf("desc match (%d) should score higher than no match (%d)", descScore, noMatchScore)
	}
	if noMatchScore != 0 {
		t.Errorf("no match should score 0, got %d", noMatchScore)
	}

	// Stars should boost score.
	withStars := relevanceScore("terraform", "", "", 6000, "terraform")
	withoutStars := relevanceScore("terraform", "", "", 0, "terraform")
	if withStars <= withoutStars {
		t.Errorf("stars should boost score: with=%d, without=%d", withStars, withoutStars)
	}

	// Unused: suppress lint for table-driven tests.
	_ = tests
}

// ============================================================================
// filterValidSkillResults tests
// ============================================================================

func TestFilterValidSkillResults(t *testing.T) {
	results := []ghSearchResult{
		{Name: "terraform", Path: "skills/terraform/SKILL.md", Repo: "owner/repo"},
		{Name: "..", Path: "skills/../SKILL.md", Repo: "owner/repo"},
		{Name: "code-review", Path: "code-review/SKILL.md", Repo: "owner/repo"},
		{Name: "", Path: "SKILL.md", Repo: "owner/repo"},
		{Name: ".hidden", Path: ".hidden/SKILL.md", Repo: "owner/repo"},
	}

	filtered := filterValidSkillResults(results)
	if len(filtered) != 2 {
		t.Fatalf("expected 2 valid results, got %d", len(filtered))
	}
	if filtered[0].Name != "terraform" {
		t.Errorf("first result should be terraform, got %q", filtered[0].Name)
	}
	if filtered[1].Name != "code-review" {
		t.Errorf("second result should be code-review, got %q", filtered[1].Name)
	}
}

// ============================================================================
// couldBeGHOwner tests
// ============================================================================

func TestCouldBeGHOwner(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"simple", "hashicorp", true},
		{"with hyphens", "my-org", true},
		{"with numbers", "org123", true},
		{"empty", "", false},
		{"too long", string(make([]byte, 40)), false},
		{"leading hyphen", "-org", false},
		{"trailing hyphen", "org-", false},
		{"spaces", "my org", false},
		{"special chars", "org@name", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := couldBeGHOwner(tt.input)
			if got != tt.expected {
				t.Errorf("couldBeGHOwner(%q) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}

// ============================================================================
// computeSkillID tests
// ============================================================================

func TestComputeSkillID(t *testing.T) {
	tests := []struct {
		name     string
		path     string
		expected string
	}{
		{"standard flat", "skills/terraform/SKILL.md", "terraform"},
		{"namespaced", "skills/author/terraform/SKILL.md", "author/terraform"},
		{"root level", "terraform/SKILL.md", "terraform"},
		{"deeply nested", "prefix/skills/terraform/SKILL.md", "terraform"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := computeSkillID(tt.path)
			if got != tt.expected {
				t.Errorf("computeSkillID(%q) = %q, want %q", tt.path, got, tt.expected)
			}
		})
	}
}
