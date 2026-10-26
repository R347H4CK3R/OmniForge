import SwiftUI

@main struct OmniForgeApp: App {
    @StateObject private var store = AssistantStore()
    var body: some Scene {
        WindowGroup { MainView().environmentObject(store) }
    }
}
