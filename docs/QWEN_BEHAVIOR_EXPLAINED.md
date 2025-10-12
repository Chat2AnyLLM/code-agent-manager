# Qwen CLI Behavior Explanation

## What You're Seeing

When you run `python -m code_assistant_manager.cli qwen`, the program:

1. **Checks if `qwen` command is installed**
2. **If NOT installed**, shows a menu:
   ```
   ╔═══════════════════════════════════════╗
   ║  Qwen Code CLI not found - Install?   ║
   ╠═══════════════════════════════════════╣
   ║  1) Yes, install now                  ║
   ║  2) No, cancel                        ║
   ║  3) Cancel                            ║
   ╚═══════════════════════════════════════╝
   ```

3. **If you select "No, cancel" (option 2)**:
   - Old behavior: Program exits silently
   - **NEW behavior (IMPROVED)**: Shows message and exits:
     ```
     Installation cancelled. Qwen Code CLI is required to proceed.
     ```

## This is NOT a Bug

The behavior you're seeing is **correct and intentional**:

- If you decline to install the required CLI tool
- The program **cannot proceed** without it
- So it exits gracefully

## How to Use Qwen CLI

### Option 1: Install When Prompted
```bash
python -m code_assistant_manager.cli qwen
# When menu appears, select option 1: "Yes, install now"
```

### Option 2: Install Manually First
```bash
# Install the Qwen CLI tool manually
npm install -g @qwen-code/qwen-code

# Then run
python -m code_assistant_manager.cli qwen
```

## What Happens After Installation

Once `qwen` is installed, the workflow becomes:

1. ✅ Check if `qwen` is installed → YES, it exists
2. Show menu: "Upgrade Qwen Code CLI?" (if you want latest version)
3. Select endpoint for Qwen API
4. Fetch available models
5. Select model
6. Launch Qwen CLI with your selected configuration

## Comparison: Before vs After Improvement

| Stage | Before | After (Improved) |
|-------|--------|------------------|
| **Cancel Installation** | Exits silently | Shows clear message explaining why |
| **User Experience** | Confusing (why did it quit?) | Clear (told CLI is required) |

## Code Change

**File:** `code_assistant_manager/tools.py`
**Method:** `_check_and_install_npm_package()`

```python
# Added this message when user cancels:
else:
    # User cancelled installation
    print(f"\n{Colors.YELLOW}Installation cancelled. {desc} is required to proceed.{Colors.RESET}")
return False
```

## Summary

**What's happening:**
- You run `python -m code_assistant_manager.cli qwen`
- Qwen CLI is not installed
- You select "No, cancel" when asked to install
- Program exits (correct behavior - can't proceed without CLI)

**What's improved:**
- Now shows a clear message explaining the CLI is required
- User understands why the program is exiting

**How to proceed:**
- Select "Yes, install now" when prompted
- OR install manually with `npm install -g @qwen-code/qwen-code`
- Then the program will continue to endpoint/model selection

---

**This is working as designed!** The program needs the CLI tool to function, so when you decline installation, it must exit.
