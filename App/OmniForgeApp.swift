import SwiftUI

@main struct OmniForgeApp: App {
    @UIApplicationDelegateAdaptor(OmniOrientationDelegate.self) private var orientationDelegate
    @StateObject private var store = AssistantStore()
    var body: some Scene {
        WindowGroup { MainView().environmentObject(store) }
    }
}
