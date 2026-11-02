import Foundation
import Security

/// Stores the device token in the Keychain rather than UserDefaults.
enum Keychain {
    private static let service = "org.resident.app"
    private static let account = "deviceToken"

    static var deviceToken: String? {
        get {
            var result: AnyObject?
            let status = SecItemCopyMatching(query(returnData: true) as CFDictionary, &result)
            guard status == errSecSuccess, let data = result as? Data else { return nil }
            return String(data: data, encoding: .utf8)
        }
        set {
            SecItemDelete(query() as CFDictionary)
            guard let newValue, !newValue.isEmpty else { return }
            var attributes = query()
            attributes[kSecValueData as String] = Data(newValue.utf8)
            attributes[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            SecItemAdd(attributes as CFDictionary, nil)
        }
    }

    private static func query(returnData: Bool = false) -> [String: Any] {
        var query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        if returnData {
            query[kSecReturnData as String] = true
            query[kSecMatchLimit as String] = kSecMatchLimitOne
        }
        return query
    }
}
