"""Shell completion commands for Code Assistant Manager.

This module contains shell completion script generation for bash and zsh.
The completion scripts provide tab-completion for all CLI commands, options,
and arguments.
"""

import typer

from code_assistant_manager.cli.app import app
from code_assistant_manager.cli.options import SHELL_OPTION


@app.command()
def completion(shell: str = SHELL_OPTION):
    """Generate shell completion scripts."""
    if shell not in ["bash", "zsh"]:
        typer.echo(f"Error: Unsupported shell {shell!r}. Supported shells: bash, zsh")
        raise typer.Exit(1)

    # Generate basic completion script with common commands
    completion_script = generate_completion_script(shell)

    typer.echo(f"# Shell completion script for {shell}")
    typer.echo("# To install, run one of the following:")
    typer.echo("#")
    typer.echo("# Option 1: Add to ~/.bashrc or ~/.zshrc")
    typer.echo(
        f"# echo 'source <(code-assistant-manager completion {shell})' >> ~/.{shell}rc"
    )
    typer.echo("#")
    typer.echo("# Option 2: Save to file and source it")
    typer.echo(
        f"# code-assistant-manager completion {shell} > ~/.{shell}_completion_code_assistant_manager"
    )
    typer.echo(
        f"# echo 'source ~/.{shell}_completion_code_assistant_manager' >> ~/.{shell}rc"
    )
    typer.echo("#")
    typer.echo(
        "# Restart your shell or run 'source ~/.bashrc' (or ~/.zshrc) to apply changes"
    )
    typer.echo()
    typer.echo("# Completion script:")
    typer.echo("=" * 50)
    typer.echo(completion_script)


@app.command("c", hidden=True)
def completion_alias_short(shell: str = SHELL_OPTION):
    """Alias for 'completion' command."""
    return completion(shell)


@app.command("comp", hidden=True)
def completion_alias(shell: str = SHELL_OPTION):
    """Alias for 'completion' command."""
    return completion(shell)


def generate_completion_script(shell: str) -> str:
    """Generate a comprehensive completion script for the given shell."""
    if shell == "bash":
        return _generate_bash_completion()
    elif shell == "zsh":
        return _generate_zsh_completion()
    else:
        return f"# Unsupported shell: {shell}"


def _generate_bash_completion() -> str:
    """Generate bash completion script."""
    return """# code-assistant-manager bash completion

_code_assistant_manager_completions()
{
    local cur prev opts base words cword
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    words="${COMP_WORDS[@]}"
    cword=$COMP_CWORD

    # Main commands (visible and hidden aliases)
    commands="launch l config cf mcp m prompt p skill s plugin pl agent ag extensions ext upgrade u install i uninstall un doctor d version v completion comp c --help --version --config --endpoints --debug -d"

    # Tool names for launch command
    tools="claude codex copilot gemini droid qwen codebuddy iflow qodercli zed neovate crush cursor-agent"

    # MCP subcommands (mcp server ...)
    mcp_server_commands="list search show add remove update"

    # Config subcommands
    config_commands="validate list ls l"

    # Prompt subcommands
    prompt_commands="list show add update remove import install uninstall status"

    # Plugin subcommands
    plugin_commands="marketplace list repos add-repo remove-repo install uninstall enable disable validate browse view status"

    # Agent subcommands
    agent_commands="list fetch view install uninstall repos add-repo remove-repo installed uninstall-all"

    # Extensions subcommands
    extensions_commands="browse install uninstall list update disable enable link new validate settings"

    # Global flags
    global_flags="--help --version --config --endpoints --debug -d"

    # Check if we have a global flag
    for ((i=1; i<cword; i++)); do
        case "${COMP_WORDS[i]}" in
            --config)
                COMPREPLY=( $(compgen -f -- ${cur}) )
                return 0
                ;;
            --endpoints)
                COMPREPLY=( $(compgen -W "all ${tools} mcp" -- ${cur}) )
                return 0
                ;;
        esac
    done

    case "${prev}" in
        launch|l)
            COMPREPLY=( $(compgen -W "${tools}" -- ${cur}) )
            return 0
            ;;
        mcp|m)
            COMPREPLY=( $(compgen -W "server" -- ${cur}) )
            return 0
            ;;
        server)
            # Check if parent is mcp
            if [ "${COMP_WORDS[1]}" = "mcp" ] || [ "${COMP_WORDS[1]}" = "m" ]; then
                COMPREPLY=( $(compgen -W "${mcp_server_commands}" -- ${cur}) )
                return 0
            fi
            ;;
        config|cf)
            COMPREPLY=( $(compgen -W "${config_commands}" -- ${cur}) )
            return 0
            ;;
        prompt|p)
            COMPREPLY=( $(compgen -W "${prompt_commands}" -- ${cur}) )
            return 0
            ;;
        skill|s)
            COMPREPLY=( $(compgen -W "${skill_commands}" -- ${cur}) )
            return 0
            ;;
        plugin|pl)
            COMPREPLY=( $(compgen -W "${plugin_commands}" -- ${cur}) )
            return 0
            ;;
        agent|ag)
            COMPREPLY=( $(compgen -W "${agent_commands}" -- ${cur}) )
            return 0
            ;;
        extensions|ext)
            COMPREPLY=( $(compgen -W "${extensions_commands}" -- ${cur}) )
            return 0
            ;;
        upgrade|u)
            COMPREPLY=( $(compgen -W "all ${tools} mcp --verbose -v" -- ${cur}) )
            return 0
            ;;
        install|i)
            COMPREPLY=( $(compgen -W "all ${tools} mcp --verbose -v" -- ${cur}) )
            return 0
            ;;
        uninstall|un)
            COMPREPLY=( $(compgen -W "all ${tools} --force -f --keep-config" -- ${cur}) )
            return 0
            ;;
        doctor|d)
            COMPREPLY=( $(compgen -W "--verbose -v" -- ${cur}) )
            return 0
            ;;
        completion|comp|c)
            COMPREPLY=( $(compgen -W "bash zsh" -- ${cur}) )
            return 0
            ;;
        --config)
            COMPREPLY=( $(compgen -f -- ${cur}) )
            return 0
            ;;
        --endpoints)
            COMPREPLY=( $(compgen -W "all ${tools} mcp" -- ${cur}) )
            return 0
            ;;
        --client|-c)
            COMPREPLY=( $(compgen -W "all ${tools}" -- ${cur}) )
            return 0
            ;;
        --scope|-s)
            COMPREPLY=( $(compgen -W "user project" -- ${cur}) )
            return 0
            ;;
        --app-type|-a)
            COMPREPLY=( $(compgen -W "claude codex gemini qwen codebuddy" -- ${cur}) )
            return 0
            ;;
        --verbose|-v)
            COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
            return 0
            ;;
        # MCP server subcommand options
        list)
            if [ "${COMP_WORDS[1]}" = "mcp" ] || [ "${COMP_WORDS[1]}" = "m" ]; then
                COMPREPLY=( $(compgen -W "--client -c --interactive -i --help" -- ${cur}) )
                return 0
            fi
            ;;
        search)
            if [ "${COMP_WORDS[1]}" = "mcp" ] || [ "${COMP_WORDS[1]}" = "m" ]; then
                COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                return 0
            fi
            ;;
        show)
            if [ "${COMP_WORDS[1]}" = "mcp" ] || [ "${COMP_WORDS[1]}" = "m" ]; then
                COMPREPLY=( $(compgen -W "--schema --help" -- ${cur}) )
                return 0
            fi
            ;;
        add)
            if [ "${COMP_WORDS[1]}" = "mcp" ] || [ "${COMP_WORDS[1]}" = "m" ]; then
                COMPREPLY=( $(compgen -W "--client -c --method -m --force -f --interactive -i --scope -s --help" -- ${cur}) )
                return 0
            fi
            ;;
        remove)
            if [ "${COMP_WORDS[1]}" = "mcp" ] || [ "${COMP_WORDS[1]}" = "m" ]; then
                COMPREPLY=( $(compgen -W "--client -c --interactive -i --scope -s --help" -- ${cur}) )
                return 0
            fi
            ;;
        update)
            if [ "${COMP_WORDS[1]}" = "mcp" ] || [ "${COMP_WORDS[1]}" = "m" ]; then
                COMPREPLY=( $(compgen -W "--client -c --interactive -i --scope -s --help" -- ${cur}) )
                return 0
            fi
            ;;
    esac

    # Check for second level completion
    if [ $cword -ge 2 ]; then
        case "${COMP_WORDS[1]}" in
            launch|l)
                case "${COMP_WORDS[2]}" in
                    claude|codex|copilot|gemini|droid|qwen|codebuddy|iflow|qodercli|zed|neovate|crush|cursor-agent)
                        COMPREPLY=( $(compgen -W "--config --help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            mcp|m)
                if [ "${COMP_WORDS[2]}" = "server" ]; then
                    if [ $cword -eq 3 ]; then
                        COMPREPLY=( $(compgen -W "${mcp_server_commands}" -- ${cur}) )
                        return 0
                    fi
                fi
                ;;
            config|cf)
                case "${COMP_WORDS[2]}" in
                    validate)
                        COMPREPLY=( $(compgen -W "--config --verbose --help" -- ${cur}) )
                        return 0
                        ;;
                    list|ls|l)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            prompt|p)
                case "${COMP_WORDS[2]}" in
                    list)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    show)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    add)
                        COMPREPLY=( $(compgen -W "--file -f --description -d --default --no-default --help" -- ${cur}) )
                        return 0
                        ;;
                    update)
                        COMPREPLY=( $(compgen -W "--file -f --description -d --name -n --default --no-default --help" -- ${cur}) )
                        return 0
                        ;;
                    remove)
                        COMPREPLY=( $(compgen -W "--force -f --help" -- ${cur}) )
                        return 0
                        ;;
                    import)
                        COMPREPLY=( $(compgen -W "--app -a --level -l --project-dir -d --description --help" -- ${cur}) )
                        return 0
                        ;;
                    install)
                        COMPREPLY=( $(compgen -W "--app -a --level -l --project-dir -d --help" -- ${cur}) )
                        return 0
                        ;;
                    uninstall)
                        COMPREPLY=( $(compgen -W "--app -a --level -l --project-dir -d --force -f --help" -- ${cur}) )
                        return 0
                        ;;
                    status)
                        COMPREPLY=( $(compgen -W "--project-dir -d --help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            skill|s)
                case "${COMP_WORDS[2]}" in
                    list|installed)
                        COMPREPLY=( $(compgen -W "--app-type -a --help" -- ${cur}) )
                        return 0
                        ;;
                    fetch|repos)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    view|delete)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    create)
                        COMPREPLY=( $(compgen -W "--title -t --content -c --description -d --tags --help" -- ${cur}) )
                        return 0
                        ;;
                    update)
                        COMPREPLY=( $(compgen -W "--title -t --content -c --description -d --tags --help" -- ${cur}) )
                        return 0
                        ;;
                    install|uninstall)
                        COMPREPLY=( $(compgen -W "--app-type -a --help" -- ${cur}) )
                        return 0
                        ;;
                    add-repo|remove-repo)
                        COMPREPLY=( $(compgen -W "--owner -o --repo -r --help" -- ${cur}) )
                        return 0
                        ;;
                    import|export)
                        COMPREPLY=( $(compgen -W "--file -f --help" -- ${cur}) )
                        return 0
                        ;;
                    uninstall-all)
                        COMPREPLY=( $(compgen -W "--app-type -a --help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            plugin|pl)
                case "${COMP_WORDS[2]}" in
                    marketplace)
                        COMPREPLY=( $(compgen -W "add list remove rm update install uninstall --help" -- ${cur}) )
                        return 0
                        ;;
                    list|repos)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    add-repo|remove-repo)
                        COMPREPLY=( $(compgen -W "--owner -o --repo -r --help" -- ${cur}) )
                        return 0
                        ;;
                    install|uninstall|enable|disable|validate)
                        COMPREPLY=( $(compgen -W "--app -a --help" -- ${cur}) )
                        return 0
                        ;;
                    browse|view|status)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            agent|ag)
                case "${COMP_WORDS[2]}" in
                    list|installed)
                        COMPREPLY=( $(compgen -W "--app -a --help" -- ${cur}) )
                        return 0
                        ;;
                    fetch|repos|view)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    install|uninstall|uninstall-all)
                        COMPREPLY=( $(compgen -W "--app -a --help" -- ${cur}) )
                        return 0
                        ;;
                    add-repo|remove-repo)
                        COMPREPLY=( $(compgen -W "--owner -o --name -n --help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            extensions|ext)
                case "${COMP_WORDS[2]}" in
                    browse|list|new|settings)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    install|uninstall|update|disable|enable|validate)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                    link)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            upgrade|u|install|i)
                case "${COMP_WORDS[2]}" in
                    all|claude|codex|copilot|gemini|droid|qwen|codebuddy|iflow|qodercli|zed|neovate|crush|cursor-agent|mcp)
                        COMPREPLY=( $(compgen -W "--verbose -v --help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            uninstall|un)
                case "${COMP_WORDS[2]}" in
                    all|claude|codex|copilot|gemini|droid|qwen|codebuddy|iflow|qodercli|zed|neovate|crush|cursor-agent)
                        COMPREPLY=( $(compgen -W "--force -f --keep-config --help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
            doctor|d)
                COMPREPLY=( $(compgen -W "--verbose -v --help" -- ${cur}) )
                return 0
                ;;
            completion|comp|c)
                case "${COMP_WORDS[2]}" in
                    bash|zsh)
                        COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
        esac
    fi

    # Complete commands
    COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
    return 0
}

complete -F _code_assistant_manager_completions code-assistant-manager
complete -F _code_assistant_manager_completions cam"""


def _generate_zsh_completion() -> str:
    """Generate zsh completion script."""
    return """# code-assistant-manager zsh completion

#compdef code-assistant-manager cam

_code_assistant_manager() {
    local -a commands tools mcp_server_commands config_commands prompt_commands skill_commands plugin_commands agent_commands extensions_commands global_flags
    local context state line

    commands=(
        'launch:Launch AI coding assistants'
        'l:Alias for launch'
        'config:Configuration management commands'
        'cf:Alias for config'
        'mcp:Manage MCP servers'
        'm:Alias for mcp'
        'prompt:Prompt management commands'
        'p:Alias for prompt'
        'skill:Skill management commands'
        's:Alias for skill'
        'plugin:Plugin management commands'
        'pl:Alias for plugin'
        'agent:Agent management commands'
        'ag:Alias for agent'
        'extensions:Manage extensions for AI assistants'
        'ext:Alias for extensions'
        'upgrade:Upgrade CLI tools'
        'u:Alias for upgrade'
        'install:Install CLI tools'
        'i:Alias for install'
        'uninstall:Uninstall CLI tools'
        'un:Alias for uninstall'
        'doctor:Run diagnostic checks'
        'd:Alias for doctor'
        'version:Show version information'
        'v:Alias for version'
        'completion:Generate shell completion scripts'
        'comp:Alias for completion'
        'c:Alias for completion'
    )

    tools=(
        'claude:Claude Code assistant'
        'codex:OpenAI Codex assistant'
        'copilot:GitHub Copilot assistant'
        'gemini:Google Gemini assistant'
        'droid:Factory.ai Droid assistant'
        'qwen:Qwen assistant'
        'codebuddy:Tencent CodeBuddy assistant'
        'iflow:iFlow assistant'
        'qodercli:Qoder assistant'
        'zed:Zed assistant'
        'neovate:Neovate assistant'
        'crush:Charmland Crush assistant'
        'cursor-agent:Cursor AI assistant'
    )

    mcp_server_commands=(
        'list:List MCP servers'
        'search:Search for MCP servers'
        'show:Show details of an MCP server'
        'add:Add MCP servers to a client'
        'remove:Remove MCP servers from a client'
        'update:Update MCP servers for a client'
    )

    config_commands=(
        'validate:Validate the configuration file'
        'list:List all configuration file locations'
        'ls:Alias for list'
        'l:Alias for list'
    )

    prompt_commands=(
        'list:List all prompts'
        'show:Show prompt content'
        'add:Add a new prompt (auto-generates fancy name)'
        'update:Update existing prompt'
        'remove:Remove a prompt'
        'import:Import from live app files (auto-generates fancy name)'
        'install:Install prompt to app files'
        'uninstall:Uninstall prompt from app files'
        'status:Show installation status'
    )

    skill_commands=(
        'list:List all skills'
        'fetch:Fetch skills from repositories'
        'view:View a specific skill'
        'create:Create a new skill'
        'update:Update an existing skill'
        'delete:Delete a skill'
        'install:Install a skill to an editor'
        'uninstall:Uninstall a skill from an editor'
        'repos:List skill repositories'
        'add-repo:Add a skill repository'
        'remove-repo:Remove a skill repository'
        'import:Import skills from file'
        'export:Export skills to file'
        'installed:List installed skills'
        'uninstall-all:Uninstall all skills from an editor'
    )

    plugin_commands=(
        'marketplace:Manage marketplaces'
        'list:List all plugins'
        'repos:List plugin repositories'
        'add-repo:Add a plugin repository'
        'remove-repo:Remove a plugin repository'
        'install:Install a plugin'
        'uninstall:Uninstall a plugin'
        'enable:Enable a plugin'
        'disable:Disable a plugin'
        'validate:Validate a plugin'
        'browse:Browse marketplace'
        'view:View plugin details'
        'status:Show plugin status'
    )

    agent_commands=(
        'list:List all agents'
        'fetch:Fetch agents from repositories'
        'view:View a specific agent'
        'install:Install an agent'
        'uninstall:Uninstall an agent'
        'repos:List agent repositories'
        'add-repo:Add an agent repository'
        'remove-repo:Remove an agent repository'
        'installed:List installed agents'
        'uninstall-all:Uninstall all agents'
    )

    extensions_commands=(
        'browse:Browse available Gemini extensions'
        'install:Install a Gemini extension'
        'uninstall:Uninstall a Gemini extension'
        'list:List installed Gemini extensions'
        'update:Update Gemini extensions'
        'disable:Disable a Gemini extension'
        'enable:Enable a Gemini extension'
        'link:Link a local Gemini extension'
        'new:Create a new Gemini extension'
        'validate:Validate a Gemini extension'
        'settings:Manage Gemini extension settings'
    )

    global_flags=(
        '--help[Show help]'
        '--version[Show version]'
        '--config[Specify config file]:file:_files'
        '--endpoints[Show tool endpoints]:endpoint:->endpoints'
        '--debug[Enable debug logging]'
        '-d[Enable debug logging]'
    )

    _arguments -C \\
        '1: :->command' \\
        '*:: :->args'

    case $state in
        command)
            _describe -t commands 'code-assistant-manager command' commands
            ;;
        args)
            case $words[1] in
                launch|l)
                    if (( CURRENT == 2 )); then
                        _describe -t tools 'AI assistant' tools
                    else
                        _values 'option' '--config[Specify config file]:file:_files' '--help[Show help]'
                    fi
                    ;;
                config|cf)
                    if (( CURRENT == 2 )); then
                        _describe -t config_commands 'config command' config_commands
                    else
                        case $words[2] in
                            validate)
                                _values 'option' '--config[Specify config file]:file:_files' '--verbose[Show verbose output]' '--help[Show help]'
                                ;;
                            *)
                                _values 'option' '--help[Show help]'
                                ;;
                        esac
                    fi
                    ;;
                mcp|m)
                    if (( CURRENT == 2 )); then
                        _values 'mcp command' 'server[Server management commands]'
                    elif (( CURRENT == 3 )) && [[ $words[2] == "server" ]]; then
                        _describe -t mcp_server_commands 'server command' mcp_server_commands
                    else
                        case $words[3] in
                            list)
                                _values 'option' '--client[Specify client]:client:(all claude codex copilot gemini droid qwen codebuddy)' '--interactive[Use interactive mode]' '--help[Show help]'
                                ;;
                            search)
                                _values 'option' '--help[Show help]'
                                ;;
                            show)
                                _values 'option' '--schema[Show raw JSON schema]' '--help[Show help]'
                                ;;
                            add)
                                _values 'option' '--client[Specify client]:client:(all claude codex copilot gemini droid qwen codebuddy)' '--method[Installation method]' '--force[Force installation]' '--interactive[Use interactive mode]' '--scope[Configuration scope]:scope:(user project)' '--help[Show help]'
                                ;;
                            remove|update)
                                _values 'option' '--client[Specify client]:client:(all claude codex copilot gemini droid qwen codebuddy)' '--interactive[Use interactive mode]' '--scope[Configuration scope]:scope:(user project)' '--help[Show help]'
                                ;;
                            *)
                                _values 'option' '--help[Show help]'
                                ;;
                        esac
                    fi
                    ;;
                prompt|p)
                    if (( CURRENT == 2 )); then
                        _describe -t prompt_commands 'prompt command' prompt_commands
                    else
                        case $words[2] in
                            list)
                                _values 'option' '--help[Show help]'
                                ;;
                            show)
                                _values 'option' '--help[Show help]'
                                ;;
                            add)
                                _values 'option' '--file[Prompt file]:file:_files' '--description[Prompt description]' '--default[Set as default]' '--no-default[Unset as default]' '--help[Show help]'
                                ;;
                            update)
                                _values 'option' '--file[Updated content file]:file:_files' '--description[Updated description]' '--name[New prompt name]' '--default[Set as default]' '--no-default[Unset as default]' '--help[Show help]'
                                ;;
                            remove)
                                _values 'option' '--force[Skip confirmation]' '--help[Show help]'
                                ;;
                            import)
                                _values 'option' '--app[Application type]:app:(claude codex gemini copilot qwen codebuddy)' '--level[Level]:level:(user project)' '--project-dir[Project directory]:directory:_files -/' '--description[Prompt description]' '--help[Show help]'
                                ;;
                            install)
                                _values 'option' '--app[Application type]:app:(claude codex gemini copilot qwen codebuddy)' '--level[Level]:level:(user project)' '--project-dir[Project directory]:directory:_files -/' '--help[Show help]'
                                ;;
                            uninstall)
                                _values 'option' '--app[Application type]:app:(claude codex gemini copilot qwen codebuddy)' '--level[Level]:level:(user project)' '--project-dir[Project directory]:directory:_files -/' '--force[Skip confirmation]' '--help[Show help]'
                                ;;
                            status)
                                _values 'option' '--project-dir[Project directory]:directory:_files -/' '--help[Show help]'
                                ;;
                            *)
                                _values 'option' '--help[Show help]'
                                ;;
                        esac
                    fi
                    ;;
                skill|s)
                    if (( CURRENT == 2 )); then
                        _describe -t skill_commands 'skill command' skill_commands
                    else
                        case $words[2] in
                            list|installed)
                                _values 'option' '--app-type[Application type]:app:(claude codex copilot gemini qwen codebuddy)' '--help[Show help]'
                                ;;
                            fetch|repos|view|delete)
                                _values 'option' '--help[Show help]'
                                ;;
                            create|update)
                                _values 'option' '--title[Skill title]' '--content[Skill content]' '--description[Skill description]' '--tags[Skill tags]' '--help[Show help]'
                                ;;
                            install|uninstall|uninstall-all)
                                _values 'option' '--app-type[Application type]:app:(claude codex copilot gemini qwen codebuddy)' '--help[Show help]'
                                ;;
                            add-repo|remove-repo)
                                _values 'option' '--owner[Repository owner]' '--repo[Repository name]' '--help[Show help]'
                                ;;
                            import|export)
                                _values 'option' '--file[File path]:file:_files' '--help[Show help]'
                                ;;
                            *)
                                _values 'option' '--help[Show help]'
                                ;;
                        esac
                    fi
                    ;;
                plugin|pl)
                    if (( CURRENT == 2 )); then
                        _describe -t plugin_commands 'plugin command' plugin_commands
                    else
                        case $words[2] in
                            marketplace)
                                _values 'option' 'add[list remove rm update install uninstall]' '--help[Show help]'
                                ;;
                            list|repos)
                                _values 'option' '--help[Show help]'
                                ;;
                            add-repo|remove-repo)
                                _values 'option' '--owner[Repository owner]' '--repo[Repository name]' '--help[Show help]'
                                ;;
                            install|uninstall|enable|disable|validate)
                                _values 'option' '--app[Application type]:app:(claude codebuddy codex copilot gemini qwen)' '--help[Show help]'
                                ;;
                            browse|view|status)
                                _values 'option' '--help[Show help]'
                                ;;
                            *)
                                _values 'option' '--help[Show help]'
                                ;;
                        esac
                    fi
                    ;;
                agent|ag)
                    if (( CURRENT == 2 )); then
                        _describe -t agent_commands 'agent command' agent_commands
                    else
                        case $words[2] in
                            list|installed)
                                _values 'option' '--app[Application type]:app:(claude codex gemini droid qwen codebuddy)' '--help[Show help]'
                                ;;
                            fetch|repos|view)
                                _values 'option' '--help[Show help]'
                                ;;
                            install|uninstall|uninstall-all)
                                _values 'option' '--app[Application type]:app:(claude codex gemini droid qwen codebuddy)' '--help[Show help]'
                                ;;
                            add-repo|remove-repo)
                                _values 'option' '--owner[Repository owner]' '--name[Repository name]' '--help[Show help]'
                                ;;
                            *)
                                _values 'option' '--help[Show help]'
                                ;;
                        esac
                    fi
                    ;;
                extensions|ext)
                    if (( CURRENT == 2 )); then
                        _describe -t extensions_commands 'extensions command' extensions_commands
                    else
                        case $words[2] in
                            browse|list|new|settings)
                                _values 'option' '--help[Show help]'
                                ;;
                            install|uninstall|update|disable|enable|validate|link)
                                _values 'option' '--help[Show help]'
                                ;;
                            *)
                                _values 'option' '--help[Show help]'
                                ;;
                        esac
                    fi
                    ;;
                upgrade|u|install|i)
                    if (( CURRENT == 2 )); then
                        local -a upgrade_targets
                        upgrade_targets=('all:Upgrade/install all tools' ${tools[@]} 'mcp:MCP servers')
                        _describe -t targets 'target' upgrade_targets
                    else
                        _values 'option' '--verbose[Show verbose output]' '--help[Show help]'
                    fi
                    ;;
                uninstall|un)
                    if (( CURRENT == 2 )); then
                        local -a uninstall_targets
                        uninstall_targets=('all:Uninstall all tools' ${tools[@]})
                        _describe -t targets 'target' uninstall_targets
                    else
                        _values 'option' '--force[Force uninstall]' '--keep-config[Keep configuration files]' '--help[Show help]'
                    fi
                    ;;
                doctor|d)
                    _values 'option' '--verbose[Show detailed output]' '--help[Show help]'
                    ;;
                version|v)
                    _values 'option' '--help[Show help]'
                    ;;
                completion|comp|c)
                    if (( CURRENT == 2 )); then
                        _values 'shell' 'bash' 'zsh'
                    else
                        _values 'option' '--help[Show help]'
                    fi
                    ;;
                --endpoints)
                    local -a endpoint_targets
                    endpoint_targets=('all' ${${tools[@]%%:*}} 'mcp')
                    _describe -t endpoints 'endpoint target' endpoint_targets
                    ;;
                *)
                    _describe -t global_flags 'global option' global_flags
                    ;;
            esac
            ;;
        endpoints)
            local -a endpoint_targets
            endpoint_targets=('all' ${${tools[@]%%:*}} 'mcp')
            _describe -t endpoints 'endpoint target' endpoint_targets
            ;;
    esac
}

_code_assistant_manager "$@"

# Also register for 'cam' alias
compdef _code_assistant_manager cam"""
