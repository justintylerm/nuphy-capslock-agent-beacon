// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "NuPhyCapsLockAgentBeacon",
    platforms: [.macOS(.v15)],
    products: [
        .executable(
            name: "nuphy-capslock-agent-beacon",
            targets: ["AgentBeacon"]
        ),
    ],
    targets: [
        .executableTarget(
            name: "AgentBeacon",
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("CoreGraphics"),
                .linkedFramework("CoreHID"),
                .linkedFramework("IOKit"),
            ]
        ),
    ]
)
