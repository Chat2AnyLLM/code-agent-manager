# Name Consistency Tests

This directory contains comprehensive tests to ensure naming consistency between `list` and `install` commands for both plugins and skills.

## Test Files

### `test_skill_name_consistency.py`
Tests for skill name consistency to prevent the bug where `cam skill list` shows a different format than what `cam skill install` expects.

**Test Classes:**
- `TestSkillNameConsistency` - Validates simplified key format generation
- `TestSkillInstallationByRepo` - Tests skills from different repository structures
- `TestRegressionPrevention` - Prevents regression of the naming bug

**Key Tests:**
- ✅ Skills with subdirectory paths show simplified keys (e.g., `owner/repo:skill` instead of `owner/repo:path/to/skill`)
- ✅ Simplified keys work with the install command
- ✅ Multiple skills from the same repo have unique keys
- ✅ No slashes appear after the colon in simplified keys

### `test_plugin_marketplace_name_consistency.py`
Tests for plugin marketplace name consistency to prevent the bug where marketplace names showed "owner/repo" format instead of the name from `marketplace.json`.

**Test Classes:**
- `TestPluginMarketplaceNameConsistency` - Validates marketplace name display
- `TestPluginMarketplaceResolution` - Tests marketplace name resolution
- `TestRegressionPrevention` - Prevents regression of the naming bug
- `TestMarketplaceInstallationScenarios` - Tests different installation scenarios

**Key Tests:**
- ✅ Marketplace names come from `repo.name` (marketplace.json), not dict keys
- ✅ No "owner/repo" format in displayed marketplace names
- ✅ Duplicate marketplaces are deduplicated
- ✅ Selected marketplace names can be resolved for installation
- ✅ Both simplified names and dict keys work for backward compatibility

## Running the Tests

### Run all consistency tests:
```bash
pytest tests/test_skill_name_consistency.py tests/test_plugin_marketplace_name_consistency.py -v
```

### Run skill tests only:
```bash
pytest tests/test_skill_name_consistency.py -v
```

### Run plugin marketplace tests only:
```bash
pytest tests/test_plugin_marketplace_name_consistency.py -v
```

### Run with verbose output:
```bash
pytest tests/test_skill_name_consistency.py -xvs
```

## What These Tests Prevent

### Skill Installation Bug
**Problem:** `cam skill list` showed keys like:
```
anthropics/skills:document-skills/docx
```

But installation with this key failed. The correct format is:
```
anthropics/skills:docx
```

**Solution:** Tests ensure the CLI displays simplified keys that work with install.

### Plugin Marketplace Bug
**Problem:** `cam plugin install frontend-design` showed marketplace options like:
```
1. claude-code-plugins
2. anthropics/claude-plugins-official  ← Wrong format
3. anthropics/claude-code              ← Wrong format
```

When selecting option 3, it failed with:
```
✗ Failed to install plugin "frontend-design@claude-code": 
  Plugin "frontend-design" not found in marketplace "claude-code"
```

**Solution:** Tests ensure:
1. Marketplace names come from `marketplace.json`, not "owner/repo" format
2. Duplicate entries are removed
3. Selected names can be resolved for installation

## Test Coverage

### Skill Tests (10 tests)
- ✅ Simplified key format validation
- ✅ Key resolution for installation
- ✅ Multiple skills from same repo
- ✅ Skills at root, in subdirectories, and nested paths
- ✅ Install key matches list display
- ✅ No slashes in simplified keys

### Plugin Marketplace Tests (13 tests)
- ✅ Marketplace name from repo object
- ✅ No slashes in marketplace names
- ✅ Deduplication of duplicate entries
- ✅ Resolution by dict key, name attribute, and alias
- ✅ No "owner/repo" format in display
- ✅ Marketplace name from marketplace.json
- ✅ Install with both simplified name and dict key

## Continuous Integration

These tests should be run in CI/CD pipelines to catch any regressions:

```yaml
# Example GitHub Actions workflow
- name: Run consistency tests
  run: |
    pytest tests/test_skill_name_consistency.py \
           tests/test_plugin_marketplace_name_consistency.py \
           --cov --cov-report=xml
```

## Adding New Tests

When adding new features related to skills or plugins:

1. **Add a test** to verify the feature works
2. **Add a regression test** to ensure naming consistency
3. **Document** what the test prevents

Example:
```python
def test_new_feature_maintains_consistency(self, tmp_path):
    """Test that new feature doesn't break name consistency."""
    # Setup
    manager = SkillManager(config_dir=tmp_path)
    
    # Test the new feature
    result = manager.new_feature()
    
    # Verify consistency
    assert "/" not in result.split(":")[-1]
    assert result in manager._load_skills()
```

## Related Issues

These tests address:
- Plugin marketplace name inconsistency: "anthropics/claude-code" vs "claude-code-plugins"
- Skill install key format: "repo:path/to/skill" vs "repo:skill"
- Duplicate marketplace entries from different config sources
- Marketplace name resolution for installation

## Maintenance

Review and update these tests when:
- Changing skill or plugin naming logic
- Modifying marketplace resolution
- Adding new configuration sources
- Updating CLI display format

## Installation Tests by Repository

### `test_installation_by_repo.py`
Comprehensive tests for installing agents, skills, and plugins from actual repositories.

**Test Classes:**
- `TestSkillInstallationByRepo` - Tests skills from anthropics, ComposioHQ, K-Dense-AI repos
- `TestAgentInstallationByRepo` - Tests agents from Dexploarer, athola, contains-studio repos
- `TestPluginInstallationByMarketplace` - Tests plugin marketplaces (anthropic, awesome-claude, superpowers)
- `TestInstallationConsistencyAcrossTypes` - Tests consistency across all three types
- `TestRealWorldInstallationScenarios` - Tests exact bug scenarios

**Key Tests:**
- ✅ Skills from anthropics/skills (docx, pdf, etc.)
- ✅ Skills from ComposioHQ/awesome-claude-skills
- ✅ Skills from K-Dense-AI/claude-scientific-skills
- ✅ Agents from Dexploarer/hyper-forge
- ✅ Agents from athola/claude-night-market
- ✅ Plugin marketplaces: anthropic-agent-skills, awesome-claude-code-plugins, superpowers-marketplace
- ✅ Consistent key format across all types
- ✅ Real-world bug scenarios (docx skill, marketplace selection)

**Running Installation Tests:**
```bash
# Run all installation tests
pytest tests/test_installation_by_repo.py -v

# Run only skill installation tests
pytest tests/test_installation_by_repo.py::TestSkillInstallationByRepo -v

# Run only agent installation tests
pytest tests/test_installation_by_repo.py::TestAgentInstallationByRepo -v

# Run only plugin marketplace tests
pytest tests/test_installation_by_repo.py::TestPluginInstallationByMarketplace -v
```

## Complete Test Suite

### Run all consistency and installation tests:
```bash
pytest tests/test_skill_name_consistency.py \
       tests/test_plugin_marketplace_name_consistency.py \
       tests/test_installation_by_repo.py -v
```

**Total: 38 tests**
- 10 skill name consistency tests
- 13 plugin marketplace name consistency tests
- 15 installation by repository tests

All tests validate:
1. Name consistency between list and install commands
2. Correct key format for each type (skill, agent, plugin)
3. Installation works from real repository configurations
4. No regression of previously reported bugs

## Test Coverage Summary

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_skill_name_consistency.py | 10 | Skill name format, resolution, regression |
| test_plugin_marketplace_name_consistency.py | 13 | Marketplace names, deduplication, resolution |
| test_installation_by_repo.py | 15 | Real repo installation, cross-type consistency |
| **Total** | **38** | **Complete coverage of naming issues** |

## Example Test Output

```bash
$ pytest tests/test_*_consistency.py tests/test_installation_by_repo.py -v

...
tests/test_skill_name_consistency.py::TestSkillNameConsistency::test_simplified_key_format PASSED
tests/test_plugin_marketplace_name_consistency.py::TestPluginMarketplaceNameConsistency::test_marketplace_name_from_repo_object PASSED
tests/test_installation_by_repo.py::TestSkillInstallationByRepo::test_install_skill_from_anthropics_skills PASSED
tests/test_installation_by_repo.py::TestPluginInstallationByMarketplace::test_anthropic_skills_marketplace PASSED
tests/test_installation_by_repo.py::TestRealWorldInstallationScenarios::test_anthropics_docx_skill_installation_path PASSED

================================================== 38 passed in 1.59s ==================================================
```

✅ All tests pass - naming consistency is maintained across skills, agents, and plugins!
