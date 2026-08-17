import AppKit
import Darwin
import Dispatch
import Foundation

private enum BeaconState: Equatable {
    case idle
    case message(Set<BeaconSource>)
    case approval(Set<BeaconSource>)

    var sources: Set<BeaconSource> {
        switch self {
        case .idle:
            return []
        case .message(let sources), .approval(let sources):
            return sources
        }
    }
}

private enum BeaconSource: String, Hashable {
    case codex
    case claude
}

private enum SourceApplication {
    static let bundleIdentifiers = [
        "codex": "com.openai.codex",
        "claude": "com.anthropic.claudefordesktop",
    ]
}

private struct PulseTiming {
    let invertedDuration: TimeInterval
    let normalDuration: TimeInterval

    static let safeDefault = PulseTiming(
        invertedDuration: 0.25,
        normalDuration: 0.25
    )

    static func load() -> PulseTiming {
        let url = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(
                "Library/Application Support/NuPhy CapsLock Agent Beacon"
            )
            .appendingPathComponent("pulse-timing.json")
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data)
                as? [String: Any],
              let inverted = object["inverted_seconds"] as? Double,
              let normal = object["normal_seconds"] as? Double,
              (0.15...5).contains(inverted),
              (0.15...5).contains(normal) else {
            return .safeDefault
        }
        return PulseTiming(
            invertedDuration: inverted,
            normalDuration: normal
        )
    }
}

private struct RequestStore: @unchecked Sendable {
    private let fileManager = FileManager.default
    private let approvalMaximumAge: TimeInterval = 30 * 60
    private let messageMaximumAge: TimeInterval = 12 * 60 * 60

    let requestsDirectory: URL
    let messagesDirectory: URL

    init() throws {
        let stateDirectory: URL
        if let override = ProcessInfo.processInfo.environment[
            "NUPHY_AGENT_BEACON_STATE_DIR"
        ], !override.isEmpty {
            stateDirectory = URL(fileURLWithPath: override, isDirectory: true)
        } else {
            let applicationSupport = try fileManager.url(
                for: .applicationSupportDirectory,
                in: .userDomainMask,
                appropriateFor: nil,
                create: true
            )
            stateDirectory = applicationSupport.appendingPathComponent(
                "NuPhy CapsLock Agent Beacon",
                isDirectory: true
            )
        }
        requestsDirectory = stateDirectory
            .appendingPathComponent("requests", isDirectory: true)
        messagesDirectory = stateDirectory
            .appendingPathComponent("messages", isDirectory: true)
        try fileManager.createDirectory(
            at: stateDirectory,
            withIntermediateDirectories: true,
            attributes: [.posixPermissions: 0o700]
        )
        try fileManager.setAttributes(
            [.posixPermissions: 0o700],
            ofItemAtPath: stateDirectory.path
        )
        try fileManager.createDirectory(
            at: requestsDirectory,
            withIntermediateDirectories: true,
            attributes: [.posixPermissions: 0o700]
        )
        try fileManager.createDirectory(
            at: messagesDirectory,
            withIntermediateDirectories: true,
            attributes: [.posixPermissions: 0o700]
        )
        try fileManager.setAttributes(
            [.posixPermissions: 0o700],
            ofItemAtPath: requestsDirectory.path
        )
        try fileManager.setAttributes(
            [.posixPermissions: 0o700],
            ofItemAtPath: messagesDirectory.path
        )
    }

    func state() -> BeaconState {
        let messageSources = unseenMessageSources()
        let approvalFiles = activeFiles(
            in: requestsDirectory,
            maximumAge: approvalMaximumAge
        )
        if !approvalFiles.isEmpty {
            return .approval(sources(for: approvalFiles))
        }
        return messageSources.isEmpty ? .idle : .message(messageSources)
    }

    private func activeFiles(
        in directory: URL,
        maximumAge: TimeInterval
    ) -> [URL] {
        guard let urls = try? fileManager.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        let cutoff = Date().addingTimeInterval(-maximumAge)
        var active: [URL] = []
        for url in urls where url.pathExtension == "json" {
            let modified = try? url.resourceValues(
                forKeys: [.contentModificationDateKey]
            ).contentModificationDate
            if let modified, modified < cutoff {
                try? fileManager.removeItem(at: url)
            } else {
                active.append(url)
            }
        }
        return active
    }

    private func source(in url: URL) -> BeaconSource? {
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data),
              let record = object as? [String: Any],
              let value = record["source"] as? String else {
            return nil
        }
        return BeaconSource(rawValue: value)
    }

    private func sources(for urls: [URL]) -> Set<BeaconSource> {
        let result = Set(urls.compactMap(source))
        // Old marker files predate source-aware lighting; keep them visible.
        return result.isEmpty && !urls.isEmpty ? [.codex] : result
    }

    private func unseenMessageSources() -> Set<BeaconSource> {
        var unseen: Set<BeaconSource> = []
        let frontmostBundleIdentifier = NSWorkspace.shared.frontmostApplication?
            .bundleIdentifier
        for url in activeFiles(
            in: messagesDirectory,
            maximumAge: messageMaximumAge
        ) {
            if let markerSource = source(in: url) {
                if SourceApplication.bundleIdentifiers[markerSource.rawValue]
                    == frontmostBundleIdentifier {
                    try? fileManager.removeItem(at: url)
                    BeaconDiagnostics.append(
                        "message-seen",
                        details: ["source": markerSource.rawValue]
                    )
                    continue
                }
                unseen.insert(markerSource)
            }
        }
        return unseen
    }
}

@main
private struct ApprovalBeacon {
    static func main() async {
        do {
            try requestCapsLockHIDAccess()
            let store = try RequestStore()
            try await runUntilTerminated(store: store)
        } catch is CancellationError {
            exit(0)
        } catch {
            NSLog("NuPhy Agent Beacon stopped safely: \(String(describing: error))")
            exit(1)
        }
    }

    private static func runUntilTerminated(store: RequestStore) async throws {
        Darwin.signal(SIGTERM, SIG_IGN)
        Darwin.signal(SIGINT, SIG_IGN)
        let worker = Task {
            try await runForever(store: store)
        }
        let termination = DispatchSource.makeSignalSource(
            signal: SIGTERM,
            queue: .global()
        )
        let interruption = DispatchSource.makeSignalSource(
            signal: SIGINT,
            queue: .global()
        )
        termination.setEventHandler { worker.cancel() }
        interruption.setEventHandler { worker.cancel() }
        termination.resume()
        interruption.resume()
        defer {
            termination.cancel()
            interruption.cancel()
        }
        try await worker.value
    }

    private static func runForever(store: RequestStore) async throws {
        while !Task.isCancelled {
            do {
                let controller = try await CapsLockLEDController.connect()
                try await controller.set(isOn: logicalCapsLockIsOn())
                BeaconDiagnostics.append(
                    "caps-controller-connected",
                    details: ["transport": controller.transportName]
                )
                do {
                    try await driveCapsLockLED(
                        controller: controller,
                        store: store
                    )
                } catch {
                    // Restore the real logical state before reconnecting. This
                    // also repairs an interrupted pulse whenever the device is
                    // still reachable.
                    try? await controller.set(isOn: logicalCapsLockIsOn())
                    throw error
                }
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                BeaconDiagnostics.append(
                    "controller-reconnecting",
                    details: ["error": String(describing: error)]
                )
                NSLog("NuPhy Agent Beacon reconnecting after: \(String(describing: error))")
                try await Task.sleep(for: .seconds(2))
            }
        }
    }

    private static func driveCapsLockLED(
        controller: CapsLockLEDController,
        store: RequestStore
    ) async throws {
        let pulseTiming = PulseTiming.load()
        var alerting = false
        var showingInvertedState = false
        var nextPulseAt = Date.distantPast
        var lastWrittenState: Bool? = logicalCapsLockIsOn()
        var lastState: BeaconState?
        while !Task.isCancelled {
            let state = store.state()
            if state != lastState {
                BeaconDiagnostics.append(
                    "beacon-state",
                    details: ["value": diagnosticName(for: state)]
                )
                lastState = state
            }
            let logicalState = logicalCapsLockIsOn()
            if !state.sources.isEmpty {
                let now = Date()
                if !alerting {
                    alerting = true
                    showingInvertedState = true
                    nextPulseAt = now.addingTimeInterval(
                        pulseTiming.invertedDuration
                    )
                    BeaconDiagnostics.append(
                        "caps-alert-started",
                        details: ["transport": controller.transportName]
                    )
                } else if now >= nextPulseAt {
                    showingInvertedState.toggle()
                    nextPulseAt = now.addingTimeInterval(
                        showingInvertedState
                            ? pulseTiming.invertedDuration
                            : pulseTiming.normalDuration
                    )
                }

                let target = showingInvertedState ? !logicalState : logicalState
                if target != lastWrittenState {
                    try await controller.set(isOn: target)
                    lastWrittenState = target
                }
            } else {
                if alerting || lastWrittenState != logicalState {
                    try await controller.set(isOn: logicalState)
                    lastWrittenState = logicalState
                }
                if alerting {
                    BeaconDiagnostics.append("caps-restored")
                }
                alerting = false
                showingInvertedState = false
                nextPulseAt = .distantPast
            }
            try await Task.sleep(for: .milliseconds(100))
        }
    }

    private static func diagnosticName(for state: BeaconState) -> String {
        switch state {
        case .idle:
            return "idle"
        case .message(let sources):
            return "message-" + sources.map(\.rawValue).sorted().joined(separator: "+")
        case .approval(let sources):
            return "approval-" + sources.map(\.rawValue).sorted().joined(separator: "+")
        }
    }

}
