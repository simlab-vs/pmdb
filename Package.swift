// swift-tools-version: 6.2
import PackageDescription

let package = Package(
  name: "PostMortemDebugger",
  platforms: [.macOS(.v15)],
  products: [
    .executable(name: "pmdb", targets: ["pmdb"]),
  ],
  dependencies: [
    .package(
      url: "https://github.com/apple/swift-algorithms.git",
      from: "1.2.0"),
    .package(
      url: "https://github.com/apple/swift-argument-parser.git",
      from: "1.7.0"),
    .package(
      url: "https://github.com/kyouko-taiga/archivist.git",
      branch: "main"),
    .package(
      url: "https://github.com/attaswift/BigInt.git",
      from: "6.0.0"),
    .package(
      url: "https://github.com/swiftlang/swift-subprocess.git",
      revision: "b3937ab85dd32f6e9435914599c1519074769c1a"), // 1.0.0
  ],
  targets: [
    .executableTarget(
      name: "pmdb",
      dependencies: [
        .target(name: "PostMortemDebugger"),
        .product(name: "ArgumentParser", package: "swift-argument-parser"),
      ]),

    .target(
      name: "PostMortemDebugger",
      dependencies: [
        .product(name: "Algorithms", package: "swift-algorithms"),
        .product(name: "Archivist", package: "archivist"),
        .product(name: "BigInt", package: "BigInt"),
      ]
    ),

    .testTarget(
      name: "PostMortemDebuggerTests",
      dependencies: [
        .target(name: "PostMortemDebugger"),
        .product(name: "Subprocess", package: "swift-subprocess"),
      ]),

    .testTarget(
      name: "pmdbTests",
      dependencies: [
        .target(name: "pmdb"),
        .product(name: "Subprocess", package: "swift-subprocess"),
      ]),
  ])
