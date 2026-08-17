import CoreGraphics
import CoreHID
import Foundation
import IOKit.hid

enum CapsLockLEDError: Error {
    case permissionDenied
    case noExactDevice
    case tooManyExactDevices
    case openFailed(IOReturn)
    case writeFailed(IOReturn)
    case updateMissing
    case identityMismatch
    case timedOut
}

func requestCapsLockHIDAccess() throws {
    if IOHIDCheckAccess(kIOHIDRequestTypeListenEvent) == kIOHIDAccessTypeGranted {
        return
    }
    guard IOHIDRequestAccess(kIOHIDRequestTypeListenEvent) else {
        throw CapsLockLEDError.permissionDenied
    }
}

func logicalCapsLockIsOn() -> Bool {
    CGEventSource.flagsState(.combinedSessionState).contains(.maskAlphaShift)
}

private enum WiredCapsIdentity {
    static let vendorID = 0x19f5
    static let productID = 0x1028
    static let manufacturer = "NuPhy"
    static let product = "Air75 V3"
    static let transport = "USB"
    static let descriptor = Data([
        0x05, 0x01, 0x09, 0x06, 0xa1, 0x01, 0x05, 0x07,
        0x19, 0xe0, 0x29, 0xe7, 0x15, 0x00, 0x25, 0x01,
        0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01,
        0x75, 0x08, 0x81, 0x01, 0x95, 0x03, 0x75, 0x01,
        0x05, 0x08, 0x19, 0x01, 0x29, 0x03, 0x91, 0x02,
        0x95, 0x05, 0x75, 0x01, 0x91, 0x01, 0x95, 0x06,
        0x75, 0x08, 0x26, 0xff, 0x00, 0x05, 0x07, 0x19,
        0x00, 0x29, 0x91, 0x81, 0x00, 0xc0,
    ])
}

private struct WiredCapsTarget {
    let device: IOHIDDevice
    let element: IOHIDElement
}

final class WiredCapsLockLEDController: @unchecked Sendable {
    private let manager: IOHIDManager
    private let targets: [WiredCapsTarget]

    init() throws {
        manager = IOHIDManagerCreate(
            kCFAllocatorDefault,
            IOOptionBits(kIOHIDOptionsTypeNone)
        )
        IOHIDManagerSetDeviceMatching(manager, [
            kIOHIDVendorIDKey: WiredCapsIdentity.vendorID,
            kIOHIDProductIDKey: WiredCapsIdentity.productID,
            kIOHIDPrimaryUsagePageKey: kHIDPage_GenericDesktop,
            kIOHIDPrimaryUsageKey: kHIDUsage_GD_Keyboard,
        ] as CFDictionary)
        let managerResult = IOHIDManagerOpen(
            manager,
            IOOptionBits(kIOHIDOptionsTypeNone)
        )
        guard managerResult == kIOReturnSuccess else {
            throw CapsLockLEDError.openFailed(managerResult)
        }

        let devices = (IOHIDManagerCopyDevices(manager) as? Set<IOHIDDevice>) ?? []
        var found: [WiredCapsTarget] = []
        for device in devices where Self.isExactKeyboardInterface(device) {
            let elements = (IOHIDDeviceCopyMatchingElements(
                device,
                nil,
                IOOptionBits(kIOHIDOptionsTypeNone)
            ) as? [IOHIDElement]) ?? []
            let capsElements = elements.filter {
                IOHIDElementGetType($0) == kIOHIDElementTypeOutput
                    && IOHIDElementGetUsagePage($0) == kHIDPage_LEDs
                    && IOHIDElementGetUsage($0) == kHIDUsage_LED_CapsLock
                    && IOHIDElementGetReportID($0) == 0
                    && IOHIDElementGetReportSize($0) == 1
            }
            guard capsElements.count == 1 else { continue }
            found.append(WiredCapsTarget(device: device, element: capsElements[0]))
        }
        guard !found.isEmpty else { throw CapsLockLEDError.noExactDevice }
        guard found.count <= 2 else { throw CapsLockLEDError.tooManyExactDevices }

        var opened: [WiredCapsTarget] = []
        do {
            for target in found {
                let result = IOHIDDeviceOpen(
                    target.device,
                    IOOptionBits(kIOHIDOptionsTypeNone)
                )
                guard result == kIOReturnSuccess else {
                    throw CapsLockLEDError.openFailed(result)
                }
                opened.append(target)
            }
        } catch {
            for target in opened {
                IOHIDDeviceClose(target.device, IOOptionBits(kIOHIDOptionsTypeNone))
            }
            throw error
        }
        targets = found
        NSLog("NuPhy Agent Beacon selected \(targets.count) exact wired Caps Lock LED interface(s).")
    }

    deinit {
        for target in targets {
            IOHIDDeviceClose(target.device, IOOptionBits(kIOHIDOptionsTypeNone))
        }
        IOHIDManagerClose(manager, IOOptionBits(kIOHIDOptionsTypeNone))
    }

    func set(isOn: Bool) throws {
        for target in targets {
            let value = IOHIDValueCreateWithIntegerValue(
                kCFAllocatorDefault,
                target.element,
                0,
                isOn ? 1 : 0
            )
            let result = IOHIDDeviceSetValue(target.device, target.element, value)
            guard result == kIOReturnSuccess else {
                throw CapsLockLEDError.writeFailed(result)
            }
        }
    }

    private static func property(_ device: IOHIDDevice, _ key: String) -> Any? {
        IOHIDDeviceGetProperty(device, key as CFString)
    }

    private static func integer(_ device: IOHIDDevice, _ key: String) -> Int? {
        (property(device, key) as? NSNumber)?.intValue
    }

    private static func string(_ device: IOHIDDevice, _ key: String) -> String? {
        property(device, key) as? String
    }

    private static func isExactKeyboardInterface(_ device: IOHIDDevice) -> Bool {
        integer(device, kIOHIDVendorIDKey) == WiredCapsIdentity.vendorID
            && integer(device, kIOHIDProductIDKey) == WiredCapsIdentity.productID
            && integer(device, kIOHIDVersionNumberKey) == 0
            && string(device, kIOHIDManufacturerKey) == WiredCapsIdentity.manufacturer
            && string(device, kIOHIDProductKey) == WiredCapsIdentity.product
            && string(device, kIOHIDTransportKey) == WiredCapsIdentity.transport
            && integer(device, kIOHIDPrimaryUsagePageKey) == kHIDPage_GenericDesktop
            && integer(device, kIOHIDPrimaryUsageKey) == kHIDUsage_GD_Keyboard
            && integer(device, kIOHIDMaxInputReportSizeKey) == 8
            && integer(device, kIOHIDMaxOutputReportSizeKey) == 1
            && (property(device, kIOHIDReportDescriptorKey) as? Data)
                == WiredCapsIdentity.descriptor
    }
}

private enum BluetoothCapsIdentity {
    static let manufacturer = "Nuphy"
    static let product = "Air75 V3-1"
    static let vendorID: UInt32 = 2007
    static let productID: UInt32 = 0
    static let versionNumber: UInt64 = 272
}

final class BluetoothCapsLockLEDController: @unchecked Sendable {
    private let client: HIDDeviceClient
    private let element: HIDElement

    private init(client: HIDDeviceClient, element: HIDElement) {
        self.client = client
        self.element = element
        NSLog("NuPhy Agent Beacon selected the exact Bluetooth Caps Lock LED interface.")
    }

    static func connect() async throws -> BluetoothCapsLockLEDController {
        try await withThrowingTaskGroup(of: BluetoothCapsLockLEDController.self) { group in
            group.addTask { try await locate() }
            group.addTask {
                try await Task.sleep(for: .seconds(5))
                throw CapsLockLEDError.timedOut
            }
            guard let result = try await group.next() else {
                throw CapsLockLEDError.timedOut
            }
            group.cancelAll()
            return result
        }
    }

    func set(isOn: Bool) async throws {
        let value = HIDElement.Value(
            element: element,
            fromIntegerTruncatingIfNeeded: isOn ? UInt8(1) : UInt8(0),
            timestamp: SuspendingClock.now
        )
        let request = HIDDeviceClient.ProvideElementUpdate(values: [value])
        let results = await client.updateElements([request], timeout: .seconds(2))
        guard let result = results[request] else {
            throw CapsLockLEDError.updateMissing
        }
        try result.get()
    }

    private static func locate() async throws -> BluetoothCapsLockLEDController {
        let manager = HIDDeviceManager()
        let criteria = HIDDeviceManager.DeviceMatchingCriteria(
            product: BluetoothCapsIdentity.product
        )
        for try await notification in await manager.monitorNotifications(
            matchingCriteria: [criteria]
        ) {
            try Task.checkCancellation()
            switch notification {
            case .deviceMatched(let reference):
                guard let client = HIDDeviceClient(deviceReference: reference) else {
                    throw CapsLockLEDError.identityMismatch
                }
                try await verify(client)
                let elements = await client.elements.filter {
                    $0.type == .output
                        && $0.usage == .led(.capsLock)
                        && $0.reportID == HIDReportID(rawValue: 6)
                }
                guard elements.count == 1 else {
                    throw CapsLockLEDError.noExactDevice
                }
                return BluetoothCapsLockLEDController(
                    client: client,
                    element: elements[0]
                )
            case .deviceRemoved:
                throw CapsLockLEDError.noExactDevice
            @unknown default:
                continue
            }
        }
        throw CapsLockLEDError.noExactDevice
    }

    private static func verify(_ client: HIDDeviceClient) async throws {
        let transport = await client.transport
        let transportIsBluetooth: Bool
        switch transport {
        case .bluetoothLowEnergy?, .bluetooth?:
            transportIsBluetooth = true
        case .unknown(let value)?:
            transportIsBluetooth = value == "Bluetooth Low Energy"
        default:
            transportIsBluetooth = false
        }
        guard await client.primaryUsage == .genericDesktop(.keyboard),
              await client.manufacturer == BluetoothCapsIdentity.manufacturer,
              await client.product == BluetoothCapsIdentity.product,
              await client.vendorID == BluetoothCapsIdentity.vendorID,
              await client.productID == BluetoothCapsIdentity.productID,
              await client.versionNumber == BluetoothCapsIdentity.versionNumber,
              transportIsBluetooth else {
            throw CapsLockLEDError.identityMismatch
        }
    }
}

enum CapsLockLEDController: Sendable {
    case wired(WiredCapsLockLEDController)
    case bluetooth(BluetoothCapsLockLEDController)

    static func connect() async throws -> CapsLockLEDController {
        do {
            return .wired(try WiredCapsLockLEDController())
        } catch CapsLockLEDError.noExactDevice {
            return .bluetooth(try await BluetoothCapsLockLEDController.connect())
        }
    }

    var transportName: String {
        switch self {
        case .wired: return "wired"
        case .bluetooth: return "bluetooth"
        }
    }

    func set(isOn: Bool) async throws {
        switch self {
        case .wired(let controller):
            try controller.set(isOn: isOn)
        case .bluetooth(let controller):
            try await controller.set(isOn: isOn)
        }
    }
}
