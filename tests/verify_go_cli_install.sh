#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

mkdir -p "$workdir/pathbin"
cat > "$workdir/pathbin/cam" <<'FAKE'
#!/usr/bin/env bash
echo "old-python-cam"
exit 42
FAKE
chmod +x "$workdir/pathbin/cam"

output=$(cd "$repo_root" && PATH="$workdir/pathbin:$PATH" INSTALL_DIR="$workdir/install-bin" CAM_CONFIG_DIR="$workdir/config" VERSION="shell-test" ./install.sh install 2>&1)

if grep -q "old-python-cam" <<<"$output"; then
    echo "install verification used PATH cam instead of INSTALL_DIR/cam" >&2
    echo "$output" >&2
    exit 1
fi

"$workdir/install-bin/cam" --version | grep -qx "shell-test"
"$workdir/install-bin/code-agent-manager" --version | grep -qx "shell-test"

CAM_CONFIG_DIR="$workdir/config" "$workdir/install-bin/cam" config list | grep -q "$workdir/config/providers.json"
CAM_CONFIG_DIR="$workdir/config" "$workdir/install-bin/cam" config list | grep -q "$workdir/config/config.yaml"

cd "$repo_root" && INSTALL_DIR="$workdir/install-bin" CAM_CONFIG_DIR="$workdir/config" ./install.sh uninstall >/dev/null
[ ! -e "$workdir/install-bin/cam" ]
[ ! -e "$workdir/install-bin/code-agent-manager" ]
