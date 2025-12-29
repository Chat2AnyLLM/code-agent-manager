import logging
from typing import List

from .base import CLITool
from .env_builder import ToolEnvironmentBuilder

logger = logging.getLogger(__name__)


class ClaudeTool(CLITool):
    """Claude CLI wrapper."""

    command_name = "claude"
    tool_key = "claude-code"
    install_description = "Claude Code CLI"

    def run(self, args: List[str] = None) -> int:
        args = args or []

        """
        Run the Claude CLI tool with the specified arguments.

        Args:
            args: List of arguments to pass to the Claude CLI

        Returns:
            Exit code of the Claude CLI process
        """
        try:
            # Set up endpoint and models for Claude
            success, result = self._validate_and_setup_tool(
                "claude", select_multiple=True
            )
            if not success:
                return 1

            # Extract endpoint configuration and selected models
            endpoint_config, endpoint_name, models_selected = result
            primary_model, secondary_model = models_selected

            # Set up environment variables for Claude using the builder
            model_vars = {
                "primary_model": primary_model,
                "secondary_model": secondary_model,
            }
            env_builder = (
                ToolEnvironmentBuilder(endpoint_config, model_vars)
                .set_base_url("ANTHROPIC_BASE_URL")
                .set_api_key("ANTHROPIC_AUTH_TOKEN")
                .set_model("ANTHROPIC_MODEL", "primary_model")
                .set_model("ANTHROPIC_SMALL_FAST_MODEL", "secondary_model")
                .set_model("CLAUDE_MODEL_2", "secondary_model")
                .set_model("ANTHROPIC_DEFAULT_SONNET_MODEL", "primary_model")
                .set_model("ANTHROPIC_DEFAULT_HAIKU_MODEL", "primary_model")
                .set_multiple_models({"CLAUDE_MODELS": "primary_model,secondary_model"})
                .set_custom_var("DISABLE_NON_ESSENTIAL_MODEL_CALLS", "1")
                .set_custom_var("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
                .set_node_tls_reject_unauthorized()
            )
            env = env_builder.build()

            # Execute the Claude CLI with the configured environment
            command = ["claude", *args]

            # Display the complete command that will be executed
            args_str = " ".join(args) if args else ""
            command_str = f"claude {args_str}".strip()
            print("")
            print("Complete command to execute:")
            print(
                f"ANTHROPIC_BASE_URL={env['ANTHROPIC_BASE_URL']} "
                f"ANTHROPIC_AUTH_TOKEN=dummy "
                f"ANTHROPIC_MODEL={primary_model} "
                f"ANTHROPIC_DEFAULT_SONNET_MODEL={primary_model} "
                f"ANTHROPIC_SMALL_FAST_MODEL={secondary_model} "
                f"ANTHROPIC_DEFAULT_HAIKU_MODEL={primary_model} "
                f"DISABLE_NON_ESSENTIAL_MODEL_CALLS=1 "
                f"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 {command_str}"
            )
            print("")
            return self._run_tool_with_env(command, env, "claude", interactive=True)
        except KeyboardInterrupt:
            logger.info("Tool execution interrupted by user")
            return 130
