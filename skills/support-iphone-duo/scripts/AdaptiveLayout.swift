import SwiftUI

/// Max widths that keep content comfortable on wide windows
/// (iPhone Duo inner display, iPad, landscape iPhone).
enum ReadableWidth {
    /// Single-column pages: onboarding, paywall, lock screen
    static let narrow: CGFloat = 480
    /// Lists, the timeline and the entry editor
    static let content: CGFloat = 700
}

extension View {
    /// Caps the width and centers the view inside whatever space it gets.
    func readableWidth(_ maxWidth: CGFloat = ReadableWidth.content, alignment: Alignment = .center) -> some View {
        frame(maxWidth: maxWidth, alignment: alignment)
            .frame(maxWidth: .infinity)
    }
}

/// Fills the available height like a plain VStack (so Spacers still work),
/// but scrolls when the window is too short for the content — for example
/// the turned outer display of iPhone Duo or a landscape iPhone.
struct FillingScrollView<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        GeometryReader { proxy in
            ScrollView {
                content
                    .frame(maxWidth: .infinity, minHeight: proxy.size.height)
            }
            .scrollBounceBehavior(.basedOnSize)
        }
    }
}

/// Single-column page whose main actions stay pinned to the bottom edge.
/// The content scrolls above them when the window is short, so the call to
/// action is always reachable.
struct PinnedActionPage<Content: View, Actions: View>: View {
    @ViewBuilder var content: Content
    @ViewBuilder var actions: Actions

    var body: some View {
        FillingScrollView {
            content
                .readableWidth(ReadableWidth.narrow)
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            actions
                .readableWidth(ReadableWidth.narrow)
                .padding(.top, 12)
                .background(Color(.systemBackground))
        }
    }
}
