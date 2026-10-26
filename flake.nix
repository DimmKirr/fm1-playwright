{
  description = "fm1-playwright development shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
      in {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.uv

            # Browser (Playwright downloads its own, but this provides system libs)
            pkgs.chromium

            # Video/audio conversion
            pkgs.ffmpeg

            # Audio routing (needed for WebAudio capture in headed mode)
            pkgs.pulseaudio

            # Virtual display for headed mode in CI
            pkgs.xorg.xorgserver
          ];

          shellHook = ''
            export PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers"
            echo "fm1-playwright dev shell"
            echo "  Run: uv sync && uv run playwright install chromium"
          '';
        };
      });
}
