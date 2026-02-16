// swift-tools-version: 6.2
import PackageDescription

let package = Package(
  name: "PostMortemDebugger",
  platforms: [.macOS(.v15)],
  products: [
    .executable(name: "pmdbg", targets: ["pmdbg"]),
  ],
  dependencies: [
    .package(
      url: "https://github.com/apple/swift-argument-parser.git",
      from: "1.7.0"),
    .package(
      url: "https://github.com/kyouko-taiga/archivist.git",
      branch: "main"),
  ],
  targets: [
    .executableTarget(
      name: "pmdbg",
      dependencies: [
        .target(name: "PostMortemDebugger"),
        .product(name: "ArgumentParser", package: "swift-argument-parser"),
      ]),

    .target(
      name: "PostMortemDebugger",
      dependencies: [
        .product(name: "Archivist", package: "archivist"),
      ]
    ),

    .testTarget(
      name: "PostMortemDebuggerTests",
      dependencies: [.target(name: "PostMortemDebugger")]),
  ])
