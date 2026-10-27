#!/usr/bin/env python3
"""Generate a compilable clean-room SwiftUI starter, not recovered source."""
import sys, zipfile, plistlib, pathlib, re, json
source=pathlib.Path(sys.argv[1]); root=pathlib.Path(sys.argv[2])
with zipfile.ZipFile(source) as z:
    names=z.namelist()
    ps=[p for p in names if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist",p)]
    if not ps: raise ValueError("IPA missing primary Info.plist")
    metadata=plistlib.loads(z.read(ps[0]))
appname=str(metadata.get("CFBundleDisplayName") or metadata.get("CFBundleName") or "ReconstructedApp")
bundle=str(metadata.get("CFBundleIdentifier") or "org.example.reconstruction")
bundle=re.sub(r"[^A-Za-z0-9.-]","",bundle)
root.mkdir(parents=True,exist_ok=True)
(root/"App").mkdir(exist_ok=True)
(root/"App"/"ReconstructionApp.swift").write_text('''import SwiftUI
@main struct ReconstructionApp: App {
    var body: some Scene { WindowGroup { ContentView() } }
}
struct ContentView: View {
    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Image(systemName: "hammer").font(.largeTitle)
                Text("Clean-room reconstruction").font(.headline)
                Text("Reimplement authorized functionality using the inventory and your own source/assets.")
                    .multilineTextAlignment(.center)
            }.padding().navigationTitle("Reconstruction")
        }
    }
}
''')
(root/"project.yml").write_text(f'''name: Reconstruction
options:
  deploymentTarget:
    iOS: "17.0"
targets:
  Reconstruction:
    type: application
    platform: iOS
    sources: [App]
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: {bundle}.cleanroom
        GENERATE_INFOPLIST_FILE: YES
        INFOPLIST_KEY_CFBundleDisplayName: Reconstruction
        SWIFT_VERSION: "5.0"
schemes:
  Reconstruction:
    build:
      targets:
        Reconstruction: all
''')
(root/"README.md").write_text(f"""# Clean-room SwiftUI starter

Source IPA app name: {appname}
Observed bundle identifier: {bundle}

This starter is ORIGINAL placeholder code. It is not decompiled or recovered application source, nor is it functionally equivalent to the analyzed app. Reimplement behavior independently using software/assets you own or have authorization to use.

Build on macOS: `brew install xcodegen && xcodegen generate && xcodebuild -project Reconstruction.xcodeproj -scheme Reconstruction -sdk iphoneos -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build`

Signing/provisioning required to install.
""")
(root/"inventory.json").write_text(json.dumps({"app_name":appname,"bundle_identifier":bundle,"entry_count":len(names),"entries":names[:5000]},indent=2))
print(root)
