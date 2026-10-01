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

          # SourceKit-LSP only accepts a toolchain that has clang, clangd, sourcekitd, swift and swiftc
          # side by side, and loads PackageDescription relative to swiftc. nixpkgs spreads these over
          # several packages, so merge them into a single toolchain for it.
          lspToolchain = pkgs.symlinkJoin {
            name = "sourcekit-lsp-toolchain";
            paths = with pkgs; [ swift swiftpm clang-tools sourcekit-lsp ];
          };
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

            # Must point to `bin`: nixpkgs patches SourceKit-LSP to always find libIndexStore, which
            # stops the toolchain search at the given directory before it looks inside `bin`.
            SOURCEKIT_TOOLCHAIN_PATH = "${lspToolchain}/bin";

            # Swift Testing captures a backtrace for every thrown error, even caught ones. With this
            # toolchain, `_Unwind_Backtrace` segfaults on the errors Swift Subprocess throws and catches
            # internally, crashing the tests that run the Python recorder.
            SWT_SWIFT_ERROR_BACKTRACING_ENABLED = "0";
          };
        });
    };
}
