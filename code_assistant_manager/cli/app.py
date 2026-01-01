import logging
import sys
from typing import List, Optional

import typer
from typer import Context

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# All imports moved inside functions to improve startup time

# Lazy-import heavy command modules to improve startup time
def _lazy_import_agent_app():
    from code_assistant_manager.cli.agents_commands import agent_app
    return agent_app

def _lazy_import_plugin_app():
    from code_assistant_manager.cli.plugin_commands import plugin_app
    return plugin_app

def _lazy_import_prompt_app():
    from code_assistant_manager.cli.prompts_commands import prompt_app
    return prompt_app

def _lazy_import_skill_app():
    from code_assistant_manager.cli.skills_commands import skill_app
    return skill_app

def _lazy_import_mcp_app():
    from code_assistant_manager.mcp.cli import app as mcp_app
    return mcp_app

def _lazy_import_extension_app():
    from code_assistant_manager.cli.extension_commands import extension_app
    return extension_app

# Logger is created lazily to improve startup time
def _get_logger():
    """Lazy logger creation to improve startup time."""
    import logging
    return logging.getLogger(__name__)

# Completion functions (lazy-loaded to improve startup time)

# Lazy-loaded completion scripts to improve startup time
_completion_scripts = {}

def _generate_completion_script(shell: str) -> str:
    """Generate a comprehensive completion script for the given shell."""
    if shell in _completion_scripts:
        return _completion_scripts[shell]

    if shell == "bash":
        script = _generate_bash_completion()
    elif shell == "zsh":
        script = _generate_zsh_completion()
    else:
        script = f"# Unsupported shell: {shell}"

    _completion_scripts[shell] = script
    return script

def _generate_bash_completion() -> str:
    """Generate bash completion script."""
    return _get_bash_completion_content()

def _get_bash_completion_content() -> str:
    """Get the bash completion script content."""
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

    # Skill subcommands
    skill_commands="list fetch view create update delete install uninstall repos add-repo remove-repo import export installed uninstall-all"

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
                    install|uninstall|update|disable|enable|validate|link)
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
    return _get_zsh_completion_content()

def _get_zsh_completion_content() -> str:
    """Get the zsh completion script content."""
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

    _arguments -C \\\\
        '1: :->command' \\\\
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
                                _values 'option' '--app[Application type]:app:(claude codex gemini copilot codebuddy)' '--level[Level]:level:(user project)' '--project-dir[Project directory]:directory:_files -/' '--description[Prompt description]' '--help[Show help]'
                                ;;
                            install)
                                _values 'option' '--app[Application type]:app:(claude codex gemini copilot codebuddy)' '--level[Level]:level:(user project)' '--project-dir[Project directory]:directory:_files -/' '--help[Show help]'
                                ;;
                            uninstall)
                                _values 'option' '--app[Application type]:app:(claude codex gemini copilot codebuddy)' '--level[Level]:level:(user project)' '--project-dir[Project directory]:directory:_files -/' '--force[Skip confirmation]' '--help[Show help]'
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
                                _values 'option' '--app[Application type]:app:(claude codebuddy codex copilot)' '--help[Show help]'
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
                        upgrade_targets=('all:Upgrade/install all tools' ${tools[@]%%:*} 'mcp:MCP servers')
                        _describe -t targets 'target' upgrade_targets
                    else
                        _values 'option' '--verbose[Show verbose output]' '--help[Show help]'
                    fi
                    ;;
                uninstall|un)
                    if (( CURRENT == 2 )); then
                        local -a uninstall_targets
                        uninstall_targets=('all:Uninstall all tools' ${tools[@]%%:*})
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

app = typer.Typer(
    name="cam",
    help="Code Assistant Manager - CLI utilities for working with AI coding assistants",
    no_args_is_help=False,
    add_completion=False,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def global_options(ctx: Context, debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging")):
    """Global options for the CLI application."""
    if debug:
        # Configure debug logging for all modules
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        _get_logger().debug("Debug logging enabled")

    # If no command is provided, show help lazily
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


# Completion commands - lightweight and always available
@app.command()
def completion(shell: str = typer.Argument(..., help="Shell type (bash, zsh)")):
    """Generate shell completion scripts."""
    if shell not in ["bash", "zsh"]:
        typer.echo(f"Error: Unsupported shell {shell!r}. Supported shells: bash, zsh")
        raise typer.Exit(1)

    # Generate basic completion script with common commands
    completion_script = _generate_completion_script(shell)

    typer.echo(f"# Shell completion script for {shell}")
    typer.echo("# To install, run one of the following:")
    typer.echo("#")
    typer.echo("# Option 1: Add to ~/.bashrc or ~/.zshrc")
    typer.echo(f"# echo 'source <(code-assistant-manager completion {shell})' >> ~/.{shell}rc")
    typer.echo("#")
    typer.echo("# Option 2: Save to file and source it")
    typer.echo(f"# code-assistant-manager completion {shell} > ~/.{shell}_completion_code_assistant_manager")
    typer.echo(f"# echo 'source ~/.{shell}_completion_code_assistant_manager' >> ~/.{shell}rc")
    typer.echo("#")
    typer.echo("# Restart your shell or run 'source ~/.bashrc' (or ~/.zshrc) to apply changes")
    typer.echo()
    typer.echo("# Completion script:")
    typer.echo("=" * 50)
    typer.echo(completion_script)

@app.command("c", hidden=True)
def completion_alias_short(shell: str = typer.Argument(..., help="Shell type (bash, zsh)")):
    """Alias for 'completion' command."""
    return completion(shell)

@app.command("comp", hidden=True)
def completion_alias(shell: str = typer.Argument(..., help="Shell type (bash, zsh)")):
    """Alias for 'completion' command."""
    return completion(shell)


# Commands are registered lazily to improve startup time

# Create a group for editor commands
editor_app = typer.Typer(
    help="Launch AI code editors: claude, codex, qwen, etc. (alias: l)",
    no_args_is_help=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


@editor_app.callback(invoke_without_command=True)
def launch(ctx: Context):
    """Launch AI code editors."""
    # If no subcommand is provided, show interactive menu to select a tool
    if ctx.invoked_subcommand is None:
        from code_assistant_manager.config import ConfigManager
        from code_assistant_manager.menu.menus import display_centered_menu
        from code_assistant_manager.tools import get_registered_tools
        from code_assistant_manager.tools.registry import TOOL_REGISTRY

        _get_logger().debug("No subcommand provided, showing interactive menu")
        # Get enabled tools from registry without loading heavy tool modules
        enabled_tools = TOOL_REGISTRY.get_enabled_tools()
        # Filter out MCP tool and sort for consistent menu display
        tool_names = sorted([t for t in enabled_tools if t != "mcp"])

        _get_logger().debug(f"Available tools for menu: {tool_names}")

        success, selected_idx = display_centered_menu(
            title="Select AI Code Editor", items=tool_names, cancel_text="Cancel"
        )

        if not success or selected_idx is None:
            _get_logger().debug("User cancelled menu selection")
            raise typer.Exit(0)

        selected_tool = tool_names[selected_idx]
        _get_logger().debug(f"User selected tool: {selected_tool}")

        # Initialize context object
        ctx.ensure_object(dict)
        ctx.obj["config_path"] = None
        ctx.obj["debug"] = False
        ctx.obj["endpoints"] = None

        # Get config and launch the selected tool
        config_path = ctx.obj.get("config_path")
        _get_logger().debug(f"Using config path: {config_path}")

        try:
            config = ConfigManager(config_path)
            is_valid, errors = config.validate_config()
            if not is_valid:
                _get_logger().error(f"Configuration validation errors: {errors}")
                typer.echo("Configuration validation errors:")
                for error in errors:
                    typer.echo(f"  - {error}")
                raise typer.Exit(1)
            _get_logger().debug("Configuration loaded and validated successfully")
        except FileNotFoundError as e:
            _get_logger().error(f"Configuration file not found: {e}")
            typer.echo(f"Error: {e}")
            raise typer.Exit(1) from e

        # Load the tool class on-demand after user selection
        registered_tools = get_registered_tools()
        
        # registered_tools keys are command_name (e.g. 'claude'), but selected_tool is registry key (e.g. 'claude-code')
        # We need to find the tool class where tool_key matches selected_tool
        tool_class = None
        
        # Direct match (e.g. 'blackbox')
        if selected_tool in registered_tools:
             tool_class = registered_tools[selected_tool]
        else:
             # Search by tool_key
             for cls in registered_tools.values():
                 # Check tool_key attribute
                 if getattr(cls, "tool_key", None) == selected_tool:
                     tool_class = cls
                     break
        
        if not tool_class:
             # Fallback: check if we can resolve command_name from registry
             tool_info = TOOL_REGISTRY.get_tool(selected_tool)
             cmd_name = tool_info.get("cli_command")
             if cmd_name and cmd_name in registered_tools:
                 tool_class = registered_tools[cmd_name]

        if not tool_class:
            typer.echo(f"Unknown tool: {selected_tool}")
            typer.echo(f"Available tools: {', '.join(sorted(registered_tools.keys()))}")
            raise typer.Exit(1)

        _get_logger().debug(f"Launching tool: {selected_tool}")
        tool_instance = tool_class(config)
        sys.exit(tool_instance.run([]))


def _create_lazy_tool_command(tool_name: str):
    """Create a lazy command for a tool that loads only when invoked."""
    def tool_command(
        ctx: Context,
        config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to settings.conf configuration file"),
    ):
        """Launch the specified AI code editor."""
        from code_assistant_manager.config import ConfigManager
        from code_assistant_manager.tools import (
            display_all_tool_endpoints,
            display_tool_endpoints,
            get_registered_tools,
        )

        # Initialize context object
        ctx.ensure_object(dict)
        ctx.obj["config_path"] = config
        ctx.obj["debug"] = False
        ctx.obj["endpoints"] = None

        # Get any extra args passed after the tool name
        tool_args = ctx.args if hasattr(ctx, 'args') else []

        _get_logger().debug(f"Executing lazy command: {tool_name} with args: {tool_args}")
        config_path = config
        _get_logger().debug(f"Using config path: {config_path}")

        # Initialize config
        try:
            config_obj = ConfigManager(config_path)
            # Validate configuration
            is_valid, errors = config_obj.validate_config()
            if not is_valid:
                _get_logger().error(f"Configuration validation errors: {errors}")
                typer.echo("Configuration validation errors:")
                for error in errors:
                    typer.echo(f"  - {error}")
                raise typer.Exit(1)
            _get_logger().debug("Configuration loaded and validated successfully")
        except FileNotFoundError as e:
            _get_logger().error(f"Configuration file not found: {e}")
            typer.echo(f"Error: {e}")
            raise typer.Exit(1) from e

        # Handle --endpoints option if specified
        endpoints = ctx.obj.get("endpoints") if ctx.obj else None
        if endpoints:
            _get_logger().debug(f"Handling endpoints option: {endpoints}")
            if endpoints == "all":
                display_all_tool_endpoints(config_obj)
            else:
                display_tool_endpoints(config_obj, endpoints)
            raise typer.Exit()

        # Get registered tools (lazy load happens here)
        registered_tools = get_registered_tools()
        if tool_name not in registered_tools:
            typer.echo(f"Unknown tool: {tool_name}")
            typer.echo(f"Available tools: {', '.join(sorted(registered_tools.keys()))}")
            raise typer.Exit(1)

        tool_class = registered_tools[tool_name]
        _get_logger().debug(f"Launching tool: {tool_name}")
        tool_instance = tool_class(config_obj)
        sys.exit(tool_instance.run(tool_args))

    # Set the command name and help text
    tool_command.__name__ = tool_name
    tool_command.__doc__ = f"Launch {tool_name} editor"
    return tool_command


# Create placeholder commands for known tools to avoid import-time loading
# These will be replaced with actual implementations when invoked
def _create_placeholder_commands():
    """Create placeholder commands that defer actual tool loading."""
    # Common tool names that users might try
    common_tools = [
        "claude", "codex", "gemini", "copilot", "cursor", "cursor-agent",
        "codebuddy", "crush", "droid", "qwen", "blackbox", "goose",
        "iflow", "neovate", "opencode", "qodercli", "zed"
    ]

    for tool_name in common_tools:
        # Create a command that will be replaced with the actual implementation on first use
        def make_placeholder(name):
            def placeholder_cmd(ctx: Context, config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to settings.conf configuration file")):
                # Replace this placeholder with the real command
                real_cmd = _create_lazy_tool_command(name)
                # Now execute it
                return real_cmd(ctx, config)
            return placeholder_cmd

        editor_app.command(
            name=tool_name,
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
        )(make_placeholder(tool_name))


# Create the placeholder commands
_create_placeholder_commands()


# Dynamically create subcommands for each editor tool
def create_editor_subcommands():
    """Create subcommands for each registered editor tool."""
    _get_logger().debug("Creating editor subcommands")
    registered_tools = get_registered_tools()
    editor_tools = {k: v for k, v in registered_tools.items() if k not in ["mcp"]}
    _get_logger().debug(f"Found {len(editor_tools)} editor tools: {list(editor_tools.keys())}")

    # Create a wrapper function with default parameters to avoid late binding issues
    def make_command(name, cls):
        def command(
            ctx: Context,
            config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to settings.conf configuration file"),
        ):
            """Launch the specified AI code editor."""
            # Initialize context object
            ctx.ensure_object(dict)
            ctx.obj["config_path"] = config
            ctx.obj["debug"] = False
            ctx.obj["endpoints"] = None

            # Get any extra args passed after the tool name
            tool_args = ctx.args if hasattr(ctx, 'args') else []
            
            _get_logger().debug(f"Executing command: {name} with args: {tool_args}")
            config_path = config
            _get_logger().debug(f"Using config path: {config_path}")

            # Initialize config
            try:
                config_obj = ConfigManager(config_path)
                # Validate configuration
                is_valid, errors = config_obj.validate_config()
                if not is_valid:
                    _get_logger().error(f"Configuration validation errors: {errors}")
                    typer.echo("Configuration validation errors:")
                    for error in errors:
                        typer.echo(f"  - {error}")
                    raise typer.Exit(1)
                _get_logger().debug("Configuration loaded and validated successfully")
            except FileNotFoundError as e:
                _get_logger().error(f"Configuration file not found: {e}")
                typer.echo(f"Error: {e}")
                raise typer.Exit(1) from e

            # Handle --endpoints option if specified
            endpoints = ctx.obj.get("endpoints") if ctx.obj else None
            if endpoints:
                _get_logger().debug(f"Handling endpoints option: {endpoints}")
                if endpoints == "all":
                    display_all_tool_endpoints(config_obj)
                else:
                    display_tool_endpoints(config_obj, endpoints)
                raise typer.Exit()

            _get_logger().debug(f"Launching tool: {name}")
            tool_instance = cls(config_obj)
            sys.exit(tool_instance.run(tool_args))

        # Set the command name and help text
        command.__name__ = name
        command.__doc__ = f"Launch {name} editor"
        return command

    for tool_name, tool_class in editor_tools.items():
        # Add the command to the editor app with context settings
        editor_app.command(
            name=tool_name,
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
        )(make_command(tool_name, tool_class))
        _get_logger().debug(f"Added command: {tool_name}")


# Create a group for config commands
config_app = typer.Typer(
    help="Configuration management commands",
    no_args_is_help=True,
)

# Add the editor app as a subcommand to the main app
app.add_typer(editor_app, name="launch")
app.add_typer(editor_app, name="l", hidden=True)
# Add the config app as a subcommand to the main app
app.add_typer(config_app, name="config")
app.add_typer(config_app, name="cf", hidden=True)

# Lazy-loaded sub-apps cache
_lazy_loaded_apps = {}

class LazyTyper:
    """A lazy wrapper for Typer apps that defers loading until first access."""

    def __init__(self, import_func, cache_key):
        self._import_func = import_func
        self._cache_key = cache_key
        self._app = None

    def _load_app(self):
        """Load the app on first access."""
        if self._app is None:
            # print(f"DEBUG: Loading app {self._cache_key}")
            if self._cache_key not in _lazy_loaded_apps:
                _lazy_loaded_apps[self._cache_key] = self._import_func()
            self._app = _lazy_loaded_apps[self._cache_key]
        return self._app

    def __getattr__(self, name):
        """Delegate attribute access to the actual app."""
        return getattr(self._load_app(), name)

# Create lazy typer wrappers that defer app loading until first access
_lazy_mcp_app = LazyTyper(_lazy_import_mcp_app, "mcp")
_lazy_prompt_app = LazyTyper(_lazy_import_prompt_app, "prompt")
_lazy_skill_app = LazyTyper(_lazy_import_skill_app, "skill")
_lazy_plugin_app = LazyTyper(_lazy_import_plugin_app, "plugin")
_lazy_agent_app = LazyTyper(_lazy_import_agent_app, "agent")
_lazy_extension_app = LazyTyper(_lazy_import_extension_app, "extension")

# Add lazy-loaded sub-apps - these will only load when the commands are actually invoked
app.add_typer(_lazy_mcp_app, name="mcp")
app.add_typer(_lazy_mcp_app, name="m", hidden=True)
app.add_typer(_lazy_prompt_app, name="prompt")
app.add_typer(_lazy_prompt_app, name="p", hidden=True)
app.add_typer(_lazy_skill_app, name="skill")
app.add_typer(_lazy_skill_app, name="s", hidden=True)
app.add_typer(_lazy_plugin_app, name="plugin")
app.add_typer(_lazy_plugin_app, name="pl", hidden=True)
app.add_typer(_lazy_agent_app, name="agent")
app.add_typer(_lazy_agent_app, name="ag", hidden=True)
app.add_typer(_lazy_extension_app, name="extensions")
app.add_typer(_lazy_extension_app, name="ext", hidden=True)

# Core commands - lightweight and always available
@app.command()
def doctor(
    ctx: Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Run diagnostic checks on the code-assistant-manager installation (alias: d)"""
    # Lazy imports for doctor command
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.cli.doctor import run_doctor_checks
    from code_assistant_manager.tools import display_all_tool_endpoints, display_tool_endpoints

    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    _get_logger().debug(f"Doctor command called with verbose: {verbose}")
    config_path = ctx.obj.get("config_path")
    _get_logger().debug(f"Using config path for doctor: {config_path}")

    # Initialize config
    try:
        config = ConfigManager(config_path)
        # Load environment variables from .env file
        config.load_env_file()
        # Validate configuration
        is_valid, errors = config.validate_config()
        if not is_valid:
            _get_logger().error(f"Configuration validation errors in doctor: {errors}")
            typer.echo("Configuration validation errors:")
            for error in errors:
                typer.echo(f"  - {error}")
            raise typer.Exit(1)
        _get_logger().debug("Configuration loaded and validated for doctor")
    except FileNotFoundError as e:
        _get_logger().error(f"Configuration file not found in doctor: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from e

    # Handle --endpoints option if specified
    endpoints = ctx.obj.get("endpoints")
    if endpoints:
        _get_logger().debug(f"Handling endpoints option in doctor: {endpoints}")
        if endpoints == "all":
            display_all_tool_endpoints(config)
        else:
            display_tool_endpoints(config, endpoints)
        raise typer.Exit()

    # Run diagnostic checks
    _get_logger().debug("Starting diagnostic checks")
    return run_doctor_checks(config, verbose)

@app.command("upgrade")
def upgrade_command(
    ctx: Context,
    target: str = typer.Argument("all", help="Tool to upgrade or 'all'"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose installer output"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Upgrade CLI tools (alias: u). If not installed, will install."""
    # Lazy imports for upgrade command
    from code_assistant_manager.cli.upgrade import handle_upgrade_command
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.tools import display_all_tool_endpoints, display_tool_endpoints, get_registered_tools

    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    _get_logger().debug(f"Upgrade command called with target: {target}")
    config_path = ctx.obj.get("config_path")
    _get_logger().debug(f"Using config path for upgrade: {config_path}")

    # Initialize config
    try:
        config = ConfigManager(config_path)
        # Validate configuration
        is_valid, errors = config.validate_config()
        if not is_valid:
            _get_logger().error(f"Configuration validation errors during upgrade: {errors}")
            typer.echo("Configuration validation errors:")
            for error in errors:
                typer.echo(f"  - {error}")
            raise typer.Exit(1)
        _get_logger().debug("Configuration validated for upgrade")
    except FileNotFoundError as e:
        _get_logger().error(f"Configuration file not found during upgrade: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1) from e

    # Handle --endpoints option if specified
    endpoints = ctx.obj.get("endpoints")
    if endpoints:
        _get_logger().debug(f"Handling endpoints option in upgrade: {endpoints}")
        if endpoints == "all":
            display_all_tool_endpoints(config)
        else:
            display_tool_endpoints(config, endpoints)
        raise typer.Exit()

    registered_tools = get_registered_tools()
    _get_logger().debug(f"Starting upgrade process for target: {target}")
    # By default run quietly; verbose flag overrides to show installer output
    import sys
    sys.exit(handle_upgrade_command(target, registered_tools, config, verbose=verbose))

@app.command("u", hidden=True)
def upgrade_alias_cmd(
    ctx: Context,
    target: str = typer.Argument("all", help="Tool to upgrade or 'all'"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Alias for 'upgrade' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return upgrade_command(ctx, target, False, config)

@app.command("install")
def install_command(
    ctx: Context,
    target: str = typer.Argument("all", help="Tool to install or 'all'"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose installer output"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Install CLI tools (alias: i). Same as upgrade - if not installed, will install. If installed, will try to upgrade."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return upgrade_command(ctx, target, verbose, config)

@app.command("i", hidden=True)
def install_alias_cmd(
    ctx: Context,
    target: str = typer.Argument("all", help="Tool to install or 'all'"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Alias for 'install' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return upgrade_command(ctx, target, False, config)

@app.command("uninstall")
def uninstall_command(
    ctx: Context,
    target: str = typer.Argument(..., help="Tool to uninstall or 'all'"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    keep_config: bool = typer.Option(False, "--keep-config", "-k", help="Keep configuration files"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Uninstall CLI tools and backup their configuration files."""
    # Lazy imports for uninstall command
    from code_assistant_manager.cli.uninstall_commands import uninstall

    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return uninstall(ctx, target, force, keep_config)

@app.command("un", hidden=True)
def uninstall_alias(
    ctx: Context,
    target: str = typer.Argument(..., help="Tool to uninstall or 'all'"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    keep_config: bool = typer.Option(False, "--keep-config", "-k", help="Keep configuration files"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Alias for 'uninstall' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return uninstall_command(ctx, target, force, keep_config, config)

@app.command("version")
def version_command():
    """Show version information."""
    from code_assistant_manager import __version__

    typer.echo(f"code-assistant-manager version {__version__}")
    raise typer.Exit()

@app.command("v", hidden=True)
def version_alias():
    """Alias for 'version' command."""
    return version_command()

@app.command("d", hidden=True)
def doctor_alias(
    ctx: Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Alias for 'doctor' command."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = False
    ctx.obj["endpoints"] = None

    return doctor(ctx, verbose, config)


@config_app.command("validate")
def validate_config(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Validate the configuration file for syntax and semantic errors."""
    from code_assistant_manager.config import ConfigManager
    from code_assistant_manager.menu.base import Colors

    try:
        cm = ConfigManager(config)
        typer.echo(
            f"{Colors.GREEN}✓ Configuration file loaded successfully{Colors.RESET}"
        )

        # Run full validation
        is_valid, errors = cm.validate_config()

        if is_valid:
            typer.echo(f"{Colors.GREEN}✓ Configuration validation passed{Colors.RESET}")
            return 0
        else:
            typer.echo(f"{Colors.RED}✗ Configuration validation failed:{Colors.RESET}")
            for error in errors:
                typer.echo(f"  - {error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except FileNotFoundError as e:
        typer.echo(f"{Colors.RED}✗ Configuration file not found: {e}{Colors.RESET}")
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"{Colors.RED}✗ Configuration validation failed: {e}{Colors.RESET}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(
            f"{Colors.RED}✗ Unexpected error during validation: {e}{Colors.RESET}"
        )
        raise typer.Exit(1)


@config_app.command("list", short_help="List all configuration file locations")
def list_config():
    """List all configuration file locations including CAM config and editor client configs."""
    from pathlib import Path

    from code_assistant_manager.menu.base import Colors

    typer.echo(f"\n{Colors.BOLD}Configuration Files:{Colors.RESET}\n")

    # CAM's own configuration
    typer.echo(f"{Colors.CYAN}Code Assistant Manager (CAM):{Colors.RESET}")
    home = Path.home()
    cam_config_locations = [
        home / ".config" / "code-assistant-manager" / "providers.json",
        Path.cwd() / "providers.json",
        home / "providers.json",
    ]
    for path in cam_config_locations:
        status = f"{Colors.GREEN}✓{Colors.RESET}" if path.exists() else " "
        typer.echo(f"  {status} {path}")

    # Editor client configurations
    typer.echo(f"\n{Colors.CYAN}Editor Client Configurations:{Colors.RESET}")

    # Define config locations for each editor with descriptions
    editor_configs = {
        "claude": {
            "description": "Claude Code Editor",
            "paths": [
                home / ".claude.json",
                home / ".claude" / "settings.json",
                home / ".claude" / "settings.local.json",
                Path.cwd() / ".claude" / "settings.json",
                Path.cwd() / ".claude" / "settings.local.json",
                Path.cwd() / ".claude" / "mcp.json",
                Path.cwd() / ".claude" / "mcp.local.json",
            ],
        },
        "cursor-agent": {
            "description": "Cursor AI Code Editor",
            "paths": [
                home / ".cursor" / "mcp.json",
                home / ".cursor" / "settings.json",
                Path.cwd() / ".cursor" / "mcp.json",
            ],
        },
        "gemini": {
            "description": "Google Gemini CLI",
            "paths": [
                home / ".gemini" / "settings.json",
                Path.cwd() / ".gemini" / "settings.json",
            ],
        },
        "copilot": {
            "description": "GitHub Copilot CLI",
            "paths": [
                home / ".copilot" / "mcp-config.json",
                home / ".copilot" / "mcp.json",
            ],
        },
        "codex": {
            "description": "OpenAI Codex CLI",
            "paths": [
                home / ".codex" / "config.toml",
            ],
        },
        "qwen": {
            "description": "Qwen Code CLI",
            "paths": [
                home / ".qwen" / "settings.json",
            ],
        },
        "codebuddy": {
            "description": "Tencent CodeBuddy CLI",
            "paths": [
                home / ".codebuddy.json",
                Path.cwd() / ".codebuddy" / "mcp.json",
            ],
        },
        "crush": {
            "description": "Charmland Crush CLI",
            "paths": [
                home / ".config" / "crush" / "crush.json",
            ],
        },
        "droid": {
            "description": "Factory.ai Droid CLI",
            "paths": [
                home / ".factory" / "mcp.json",
                home / ".factory" / "settings.json",
            ],
        },
        "iflow": {
            "description": "iFlow CLI",
            "paths": [
                home / ".iflow" / "settings.json",
                home / ".iflow" / "config.json",
            ],
        },
        "neovate": {
            "description": "Neovate Code CLI",
            "paths": [
                home / ".neovate" / "config.json",
            ],
        },
        "qodercli": {
            "description": "Qoder CLI",
            "paths": [
                home / ".qodercli" / "config.json",
            ],
        },
        "zed": {
            "description": "Zed Editor",
            "paths": [
                home / ".config" / "zed" / "settings.json",
            ],
        },
    }

    for editor, config_info in editor_configs.items():
        description = config_info.get("description", editor.capitalize())
        paths = config_info.get("paths", [])
        typer.echo(f"\n  {Colors.BOLD}{description} ({editor}):{Colors.RESET}")
        for path in paths:
            status = f"{Colors.GREEN}✓{Colors.RESET}" if path.exists() else " "
            typer.echo(f"    {status} {path}")

    typer.echo()


def parse_toml_key_path(key_path):
    """Parse a dotted key path that may contain TOML quoted keys.

    Examples:
        codex.profiles.myprofile.model -> ['codex', 'profiles', 'myprofile', 'model']
        codex.profiles."alibaba/glm-4.5".model -> ['codex', 'profiles', 'alibaba/glm-4.5', 'model']
        codex.profiles."alibaba/deepseek-v3.2-exp" -> ['codex', 'profiles', 'alibaba/deepseek-v3.2-exp']
    """
    import re

    # First, split by dots but preserve quoted strings
    # Use a regex that matches quoted strings OR unquoted parts
    parts = re.split(r'(?<!\\)"(?:\\.|[^"\\])*"(?:\s*\.\s*|\s*$)|\s*\.\s*', key_path.strip())

    # Clean up the parts - remove empty strings and whitespace
    cleaned_parts = []
    for part in parts:
        part = part.strip()
        if part and part not in ['.', '']:
            # Remove surrounding quotes if present
            if part.startswith('"') and part.endswith('"'):
                part = part[1:-1].replace('\\"', '"')
            cleaned_parts.append(part)

    return cleaned_parts


@config_app.command("set", short_help="Set a configuration value for code assistants")


def set_config(


    key_value: str = typer.Argument(


        ...,


        help="Configuration key=value pair (e.g., codex.profiles.grok-code-fast-1.model=qwen3-coder-plus)",


    ),


    scope: str = typer.Option("user", "--scope", "-s", help="Configuration scope (user, project)"),


):


    """Set a configuration value for code assistants.





    Supports dotted key notation for nested configuration values.


    Examples:


        cam config set codex.model=gpt-4


        cam config set --scope project claude.theme=dark


        cam config set codex.profiles.my-profile.model=qwen3-coder-plus


    """


    from code_assistant_manager.configs import get_tool_config


    from code_assistant_manager.menu.base import Colors





    try:


        # Parse key=value


        if "=" not in key_value:


            typer.echo(


                f"{Colors.RED}✗ Invalid format. Use key=value syntax{Colors.RESET}"


            )


            raise typer.Exit(1)





        key_path, value = key_value.split("=", 1)


        key_path = key_path.strip()


        value = value.strip()





        # Parse dotted key path using TOML-aware parser


        # We need to extract the prefix (tool name) first


        # But wait, BaseToolConfig._parse_key_path does splitting too.


        # However, we need to know WHICH tool to load first.


        # So we reuse the parse_toml_key_path helper here for now or duplicate logic.


        parts = parse_toml_key_path(key_path)


        if len(parts) < 2:


            typer.echo(


                f"{Colors.RED}✗ Invalid key format. Use prefix.key.path format{Colors.RESET}"


            )


            raise typer.Exit(1)





        prefix = parts[0]  # e.g., "codex"


        config_key = ".".join(parts[1:])  # Reconstruct the key without prefix





        # Get tool config


        tool_config = get_tool_config(prefix)


        if not tool_config:


            typer.echo(


                f"{Colors.RED}✗ Unsupported config prefix (tool): {prefix}{Colors.RESET}"


            )


            raise typer.Exit(1)





        # Set value


        saved_path = tool_config.set_value(config_key, value, scope)





        typer.echo(


            f"{Colors.GREEN}✓ Set {key_path} = {value} ({scope} scope){Colors.RESET}"


        )


        typer.echo(f"  Config: {saved_path}")





    except typer.Exit:


        raise


    except Exception as e:


        typer.echo(f"{Colors.RED}✗ Failed to set config value: {e}{Colors.RESET}")


        raise typer.Exit(1)








@config_app.command("unset", short_help="Unset a configuration value for code assistants")


def unset_config(


    key_path: str = typer.Argument(


        ..., help="Configuration key path (e.g., codex.profiles.grok-code-fast-1.model)"


    ),


    scope: str = typer.Option("user", "--scope", "-s", help="Configuration scope (user, project)"),


):


    """Unset a configuration value for code assistants.





    Supports dotted key notation for nested configuration values.


    Examples:


        cam config unset codex.model


        cam config unset --scope project claude.theme


        cam config unset codex.profiles.my-profile.model


    """


    from code_assistant_manager.configs import get_tool_config


    from code_assistant_manager.menu.base import Colors





    try:


        key_path = key_path.strip()





        # Parse dotted key path


        parts = parse_toml_key_path(key_path)


        if len(parts) < 2:


            typer.echo(


                f"{Colors.RED}✗ Invalid key format. Use prefix.key.path format{Colors.RESET}"


            )


            raise typer.Exit(1)





        prefix = parts[0]


        config_key = ".".join(parts[1:])





        # Get tool config


        tool_config = get_tool_config(prefix)


        if not tool_config:


            typer.echo(


                f"{Colors.RED}✗ Unsupported config prefix (tool): {prefix}{Colors.RESET}"


            )


            raise typer.Exit(1)





        found = tool_config.unset_value(config_key, scope)





        if not found:


            typer.echo(


                f"{Colors.YELLOW}! Key '{key_path}' not found in {scope} config{Colors.RESET}"


            )


            raise typer.Exit(0)





        typer.echo(


            f"{Colors.GREEN}✓ Unset {key_path} from {scope} scope{Colors.RESET}"


        )





    except typer.Exit:


        raise


    except Exception as e:


        typer.echo(f"{Colors.RED}✗ Failed to unset config value: {e}{Colors.RESET}")


        raise typer.Exit(1)








def flatten_config(data: dict, prefix: str = "") -> dict:


    """Flatten nested dictionary into dotted notation."""


    result = {}





    def _flatten(obj, current_prefix):


        if isinstance(obj, dict):


            for key, value in obj.items():


                new_prefix = f"{current_prefix}.{key}" if current_prefix else key


                _flatten(value, new_prefix)


        elif isinstance(obj, list):


            # For lists, convert to string representation


            result[current_prefix] = str(obj)


        else:


            # Convert all values to strings


            result[current_prefix] = str(obj)





    _flatten(data, prefix)


    return result








@config_app.command("show", short_help="Show configuration in dotted format")


def show_config(


    key_path: Optional[str] = typer.Argument(


        None, help="Specific config key path to show (optional)"


    ),


    app: str = typer.Option(


        "claude", "-a", "--app", help="App to show config for (default: claude)"


    ),


    scope: Optional[str] = typer.Option(


        None, "--scope", "-s", help="Filter by scope (user, project)"


    ),


):


    """Show configuration for an AI editor app in dotted notation format.





    Examples:


        cam config show                    # Show all claude config


        cam config show -a codex          # Show all codex config


        cam config show --scope project    # Show only project config


        cam config show claude.tipsHistory.config-thinking-mode  # Show specific key


    """


    from code_assistant_manager.configs import get_tool_config


    from code_assistant_manager.menu.base import Colors





    try:


        tool_config = get_tool_config(app)


        if not tool_config:


            typer.echo(f"{Colors.RED}✗ Unknown app: {app}{Colors.RESET}")


            raise typer.Exit(1)





        # Load configs


        # If specific scope requested, we get a dict with just that scope (BaseToolConfig returns same structure if scope arg is passed? No, check implementation)


        # BaseToolConfig.load_config(scope) returns JUST the data dict for that scope if scope is provided.


        # But existing logic expects a structure mapping scope -> {data, path}.


        # So I need to adapt the usage or the BaseToolConfig.load_config behavior.


        # BaseToolConfig.load_config(None) returns scope mapping. That fits.


        


        if scope:


             # Just load all and filter here to keep consistent structure for display logic below


             all_configs = tool_config.load_config()


             if scope not in all_configs:


                typer.echo(


                    f"{Colors.YELLOW}No configuration found for {app} in scope '{scope}'{Colors.RESET}"


                )


                return


             configs_to_show = {scope: all_configs[scope]}


        else:


             all_configs = tool_config.load_config()


             configs_to_show = all_configs





        if not configs_to_show:


            typer.echo(f"{Colors.YELLOW}No configuration found for {app}{Colors.RESET}")


            return





        # Collect and flatten all requested configs


        merged_flattened = {}


        key_sources = {}





        # Sort scopes so that project overrides user in the merged view


        for s_name in ["user", "project"]:


            if s_name in configs_to_show:


                s_data = configs_to_show[s_name]["data"]


                s_path = configs_to_show[s_name]["path"]


                flattened = flatten_config(s_data, app)


                for k, v in flattened.items():


                    merged_flattened[k] = v


                    key_sources[k] = (s_name, s_path)





        if not merged_flattened:


            typer.echo(f"{Colors.YELLOW}No keys found in requested scope(s){Colors.RESET}")


            return





        # Header


        typer.echo(f"{Colors.CYAN}{app.upper()} Configuration:{Colors.RESET}")


        for s_name, s_info in configs_to_show.items():


            typer.echo(f"  {Colors.BOLD}[{s_name}]{Colors.RESET} {s_info['path']}")


        typer.echo()





        # Filter by key_path if provided


        keys_to_show = sorted(merged_flattened.keys())


        if key_path:


            import re





            if "*" in key_path:


                pattern = re.escape(key_path).replace(r"\*", "[^.]+")


                regex = re.compile(f"^{pattern}$")


                keys_to_show = [k for k in keys_to_show if regex.match(k)]


            else:


                # Direct match or prefix match


                keys_to_show = [


                    k


                    for k in keys_to_show


                    if k == key_path or k.startswith(key_path + ".")


                ]





            if not keys_to_show:


                typer.echo(


                    f"{Colors.RED}✗ Key '{key_path}' not found in {app} configuration{Colors.RESET}"


                )


                raise typer.Exit(1)





        # Display keys


        for key in keys_to_show:


            value = merged_flattened[key]


            s_name, s_path = key_sources[key]


            scope_tag = f" {Colors.DIM}({s_name}){Colors.RESET}" if not scope else ""


            typer.echo(f"{Colors.GREEN}{key}{Colors.RESET} = {value}{scope_tag}")





    except Exception as e:


        typer.echo(f"{Colors.RED}✗ Failed to show config: {e}{Colors.RESET}")


        raise typer.Exit(1)

