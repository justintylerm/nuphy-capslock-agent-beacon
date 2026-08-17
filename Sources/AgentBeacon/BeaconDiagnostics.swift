import Foundation

enum BeaconDiagnostics {
    private static let maximumBytes: UInt64 = 512 * 1024

    static func append(_ event: String, details: [String: String] = [:]) {
        guard let directory = try? stateDirectory() else { return }
        let url = directory.appendingPathComponent("events.log")
        rotateIfNeeded(url)

        var record = details
        record["at"] = ISO8601DateFormatter().string(from: Date())
        record["event"] = event
        guard let data = try? JSONSerialization.data(
            withJSONObject: record,
            options: [.sortedKeys]
        ) else { return }

        var line = data
        line.append(0x0a)
        if !FileManager.default.fileExists(atPath: url.path) {
            FileManager.default.createFile(
                atPath: url.path,
                contents: nil,
                attributes: [.posixPermissions: 0o600]
            )
        }
        guard let handle = try? FileHandle(forWritingTo: url) else { return }
        defer { try? handle.close() }
        do {
            try handle.seekToEnd()
            try handle.write(contentsOf: line)
        } catch {
            return
        }
    }

    private static func stateDirectory() throws -> URL {
        if let override = ProcessInfo.processInfo.environment[
            "NUPHY_AGENT_BEACON_STATE_DIR"
        ], !override.isEmpty {
            let directory = URL(fileURLWithPath: override, isDirectory: true)
            try FileManager.default.createDirectory(
                at: directory,
                withIntermediateDirectories: true,
                attributes: [.posixPermissions: 0o700]
            )
            try FileManager.default.setAttributes(
                [.posixPermissions: 0o700],
                ofItemAtPath: directory.path
            )
            return directory
        }
        let applicationSupport = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let directory = applicationSupport.appendingPathComponent(
            "NuPhy CapsLock Agent Beacon",
            isDirectory: true
        )
        try FileManager.default.createDirectory(
            at: directory,
            withIntermediateDirectories: true,
            attributes: [.posixPermissions: 0o700]
        )
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o700],
            ofItemAtPath: directory.path
        )
        return directory
    }

    private static func rotateIfNeeded(_ url: URL) {
        guard let values = try? url.resourceValues(forKeys: [.fileSizeKey]),
              UInt64(values.fileSize ?? 0) >= maximumBytes else { return }
        let previous = url.deletingLastPathComponent()
            .appendingPathComponent("events.previous.log")
        try? FileManager.default.removeItem(at: previous)
        try? FileManager.default.moveItem(at: url, to: previous)
    }
}
