---
title: Capped Launch Model Picker Design
date: 2026-06-16
---

# Capped Launch Model Picker Design

## Goal

When `cam launch` reaches model selection, avoid filling the terminal with every advertised model. The model picker should show a small preview of up to 15 models, while still allowing the user to type and filter across the full discovered model list.

## Current Behavior

`runLaunchWizard` builds the model picker in `internal/cli/launch_wizard.go`. The picker uses the shared `pickerStep` component from `internal/cli/tool_menu.go`. `pickerStep` already supports keyboard filtering, but when no filter is entered its `visible()` method returns all items. For endpoints with many models, the initial model selection screen consumes the whole terminal.

## Proposed Approach

Add an optional visible item limit to `pickerStep` and use it only for the launch model picker.

The existing `newPickerStep(title, items, hint)` constructor will remain unchanged, so existing tool and provider pickers keep their current unlimited behavior. A new helper, such as `newLimitedPickerStep(title, items, hint, limit)`, will create a picker with a positive display limit.

`pickerStep.visible()` will continue to filter against the full `items` slice. After filtering, it will cap the returned list when `visibleLimit > 0`. This means:

- the unfiltered model list initially shows at most 15 models;
- typing a filter still searches every discovered model, including models outside the initial preview;
- filtered results also stay capped at 15 to protect the terminal;
- regular pickers remain unchanged because their limit is zero.

## Components

- `internal/cli/tool_menu.go`
  - Add `visibleLimit int` to `pickerStep`.
  - Add a limited picker constructor/helper.
  - Apply the limit at the end of `visible()`.

- `internal/cli/launch_wizard.go`
  - Define or use a model picker limit of 15.
  - Build the model picker with the limited helper.
  - Update the hint to make typing-to-filter clear.

- Tests
  - Verify normal pickers remain unlimited.
  - Verify limited pickers cap visible results to 15.
  - Verify filtering searches all items, including matches outside the initial 15.
  - Verify the launch wizard model picker uses the 15-item limit.

## Data Flow

1. `buildModelStep()` resolves all models for the selected endpoint.
2. It passes the complete model slice into the limited picker.
3. The picker stores the complete list in `items`.
4. On render or selection, `visible()` filters the complete list, then caps what is displayed.
5. `selected()` returns the highlighted item from the currently visible capped result.

## Error Handling and Edge Cases

- If model discovery fails or returns no models, existing manual entry behavior remains unchanged.
- If fewer than 15 models are available, all are displayed.
- If the filter has no matches, existing “No items match your filter.” behavior remains unchanged.
- Cursor clamping remains safe because movement, selection, and rendering already use `visible()`.

## Testing Strategy

This is a Go CLI behavior change. Add focused unit coverage around the picker and launch wizard model step. Per repository instructions, after code changes find all relevant test files and run them one by one. If only the design document changes, no tests are required.
