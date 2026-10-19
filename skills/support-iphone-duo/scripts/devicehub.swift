// Drives Xcode Device Hub through the macOS Accessibility API, so an agent can
// change iPhone Duo poses without screen clicks.
//
// Build:  swiftc -O devicehub.swift -o devicehub
// Usage:  ./devicehub press "Open"            # Closed | Partially Open | Open | Rotate Right | Home ...
//         ./devicehub menu Controls "Rotate Right"
//         ./devicehub dump [depth]            # print the window tree to find control names
//
// Needs Accessibility permission for the app that runs this (System Settings >
// Privacy & Security > Accessibility). The user must grant it; never change it yourself.
import AppKit
import ApplicationServices

// NSRunningApplication reports pid -1 for Device Hub, and System Events reports
// unix id 0, so find the process with pgrep instead.
func deviceHubPID() -> pid_t? {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
    p.arguments = ["-f", "DeviceHub.app/Contents/MacOS/DeviceHub"]
    let pipe = Pipe(); p.standardOutput = pipe
    try? p.run(); p.waitUntilExit()
    let out = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
    return out.split(separator: "\n").first.flatMap { pid_t($0) }
}

func attr(_ e: AXUIElement, _ k: String) -> AnyObject? {
    var v: AnyObject?
    return AXUIElementCopyAttributeValue(e, k as CFString, &v) == .success ? v : nil
}
func kids(_ e: AXUIElement) -> [AXUIElement] { attr(e, kAXChildrenAttribute) as? [AXUIElement] ?? [] }
func label(_ e: AXUIElement) -> [String] {
    [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute].compactMap { attr(e, $0) as? String }
}

func findButton(_ e: AXUIElement, _ name: String, _ depth: Int = 0) -> AXUIElement? {
    if (attr(e, kAXRoleAttribute) as? String) == "AXButton", label(e).contains(name) { return e }
    guard depth < 20 else { return nil }
    for k in kids(e) where (attr(k, kAXRoleAttribute) as? String) != "AXMenuBar" {
        if let f = findButton(k, name, depth + 1) { return f }
    }
    return nil
}

func dump(_ e: AXUIElement, _ depth: Int, _ maxDepth: Int) {
    let role = attr(e, kAXRoleAttribute) as? String ?? "?"
    print(String(repeating: "  ", count: depth) + role + " | " + label(e).joined(separator: " | "))
    guard depth < maxDepth else { return }
    for k in kids(e) { dump(k, depth + 1, maxDepth) }
}

let args = Array(CommandLine.arguments.dropFirst())
guard AXIsProcessTrusted() else { print("Not trusted: grant Accessibility permission first"); exit(2) }
guard let pid = deviceHubPID() else { print("Device Hub is not running"); exit(1) }
let app = AXUIElementCreateApplication(pid)
let windows = attr(app, kAXWindowsAttribute) as? [AXUIElement] ?? []

switch args.first {
case "press":
    let name = args[1]
    guard let b = windows.lazy.compactMap({ findButton($0, name) }).first ?? findButton(app, name) else {
        print("not found: \(name) (windows: \(windows.count)). Run `dump` to see the tree."); exit(1)
    }
    print("press \(name):", AXUIElementPerformAction(b, kAXPressAction as CFString) == .success ? "ok" : "failed")
case "menu":
    guard let bar = attr(app, kAXMenuBarAttribute),
          let top = kids(bar as! AXUIElement).first(where: { label($0).contains(args[1]) }),
          let menu = kids(top).first,
          let item = kids(menu).first(where: { label($0).contains(args[2]) }) else {
        print("menu item not found (disabled items vanish when no device is selected)"); exit(1)
    }
    print("menu \(args[2]):", AXUIElementPerformAction(item, kAXPressAction as CFString) == .success ? "ok" : "failed")
case "dump":
    let depth = args.count > 1 ? Int(args[1]) ?? 12 : 12
    for w in windows { dump(w, 0, depth) }
default:
    print("usage: devicehub press <name> | menu <Menu> <Item> | dump [depth]")
}
