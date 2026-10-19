import XCTest

/// Template: temporary screen tour for iPhone Duo checks.
/// Copy into a `<App>UITests` UI-testing target, replace the tour steps with
/// your app's screens, run once per pose, then delete the target.
///
/// Run with:
///   TEST_RUNNER_SHOT_DIR=<dir> TEST_RUNNER_POSE=open xcodebuild test ... \
///     -only-testing:<App>UITests/ScreenTourUITests/testTourCurrentPose
/// while duo-capture-watcher.sh watches <dir>.
final class ScreenTourUITests: XCTestCase {
    private var shotDir: String { ProcessInfo.processInfo.environment["SHOT_DIR"] ?? NSTemporaryDirectory() }
    private var pose: String { ProcessInfo.processInfo.environment["POSE"] ?? "pose" }

    override func setUp() {
        continueAfterFailure = true
    }

    /// Keep the orientation Device Hub set. XCUIDevice.orientation has no effect on the Duo.
    func testTourCurrentPose() {
        // Launch arguments "-key value" override UserDefaults / @AppStorage for one launch.
        var app = launch(["-hasCompletedOnboarding", "NO"])
        shot("01-onboarding")
        tapIfExists(app.buttons["Continue"])
        shot("02-onboarding-2", delay: 1)
        app.terminate()

        app = launch(["-hasCompletedOnboarding", "YES"])
        shot("03-home", delay: 1)
        // Open menus by accessibility label, then menu items by title.
        tapIfExists(app.buttons["Menu"])
        tapIfExists(app.buttons["Settings"].firstMatch)
        shot("04-settings", delay: 1)
        tapIfExists(app.buttons["Done"])
        app.terminate()
    }

    // MARK: - Helpers

    private func launch(_ arguments: [String]) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = arguments
        app.launch()
        sleep(2)
        return app
    }

    private func tapIfExists(_ element: XCUIElement) {
        guard element.waitForExistence(timeout: 2) else { return }
        // Buttons in a scrolled grid can report isHittable == false; tap the center instead.
        if element.isHittable { element.tap() } else { element.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap() }
    }

    /// Asks the host watcher to capture both displays, then waits for it.
    private func shot(_ name: String, delay: Double = 0) {
        if delay > 0 { Thread.sleep(forTimeInterval: delay) }
        let fm = FileManager.default
        try? fm.createDirectory(atPath: shotDir, withIntermediateDirectories: true)
        let base = URL(fileURLWithPath: shotDir)
        let id = "\(pose)-\(name)"
        let done = base.appendingPathComponent("\(id).done")
        try? fm.removeItem(at: done)
        try? Data().write(to: base.appendingPathComponent("\(id).ready"))
        let deadline = Date().addingTimeInterval(20)
        while !fm.fileExists(atPath: done.path), Date() < deadline {
            Thread.sleep(forTimeInterval: 0.2)
        }
    }
}
