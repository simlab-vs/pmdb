{
  description = "pytrace-recorder — the pmdb post-mortem debugger and its Python recorder library";

  # Pinned to an unstable version until we get a stable release with Swift 6.2 support.
  inputs.nixpkgs.url = "github:nixos/nixpkgs/b4fd65b198c599cbe814fcb9f42d25d021595ec9";

  outputs = { self, nixpkgs }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              swift # 6.2.4
              swiftpm 
              swift-format
              sourcekit-lsp
              python3
            ];
          };
        });
    };
}
