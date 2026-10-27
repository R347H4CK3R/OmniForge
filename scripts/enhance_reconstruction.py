#!/usr/bin/env python3
"""Enhance a clean-room SwiftUI scaffold with editable screens and evidence links."""
import json, pathlib, re, sys, shutil
project=pathlib.Path(sys.argv[1])
evidence=pathlib.Path(sys.argv[2])
project.mkdir(parents=True,exist_ok=True)
app=project/"App"
app.mkdir(parents=True,exist_ok=True)
reference=project/"Evidence"
reference.mkdir(exist_ok=True)
for file in ("ui_inventory.json","class_method_evidence.json","UI_RECONSTRUCTION.md","screenshots.json","interface_evidence.json","SCREEN_REBUILD_CHECKLIST.md"):
    source=evidence/file
    if source.is_file() and source.stat().st_size<10_000_000:
        shutil.copyfile(source,reference/file)
screens=[]
manifest=evidence/"screenshots.json"
if manifest.exists():
    data=json.loads(manifest.read_text())
    for index,item in enumerate(data[:35]):
        filename=str(item.get("file",""))
        if not re.fullmatch(r"[A-Za-z0-9_.-]+",filename):continue
        screenshot=evidence/"Screenshots"/filename
        if screenshot.exists() and screenshot.stat().st_size<18_000_000:
            screens.append({"index":index+1,"file":filename,"title":"Reference "+str(index+1)})
            folder=project/"ReferenceScreenshots"
            folder.mkdir(exist_ok=True)
            shutil.copyfile(screenshot,folder/filename)
if not screens:screens=[{"index":1,"title":"Home (placeholder)","file":None}]
swift='''import SwiftUI

// Clean-room placeholders. Labels and behavior must be validated against permitted reference evidence.
struct ScreenDescriptor: Identifiable {
    let id: Int
    let title: String
    let screenshotName: String?
}

struct ContentView: View {
    private let screens: [ScreenDescriptor] = [
'''
for item in screens:
    title=item["title"].replace('"','')
    name='"'+item["file"]+'"' if item["file"] else "nil"
    swift+=f'        ScreenDescriptor(id: {item["index"]}, title: "{title}", screenshotName: {name}),\n'
swift+='''    ]
    var body: some View {
        NavigationStack {
            List(screens) { screen in
                NavigationLink(screen.title) { ScreenEditorView(screen: screen) }
            }.navigationTitle("Reconstruction")
        }
    }
}

struct ScreenEditorView: View {
    let screen: ScreenDescriptor
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(screen.title).font(.title2)
                Text("Original implementation placeholder. Use screenshots and observed behavior to implement authorized functionality.")
                    .font(.callout)
                if let name = screen.screenshotName {
                    Text("Reference evidence: " + name).font(.caption)
                }
                Button("Example action") { }
                    .buttonStyle(.borderedProminent)
            }.padding()
        }.navigationTitle(screen.title)
    }
}
'''
(app/"ContentView.swift").write_text(swift)
main=app/"ReconstructionApp.swift"
main.write_text('''import SwiftUI
@main struct ReconstructionApp: App {
    var body: some Scene { WindowGroup { ContentView() } }
}
''')
(project/"SCREEN_CATALOG.json").write_text(json.dumps(screens,indent=2))
with (project/"README.md").open("a") as f:
    f.write("\n## Editable reconstruction workspace\n\nContentView.swift contains screen entries based on supplied screenshots, or a placeholder if none were provided. Evidence/ holds inventories and symbol clues. ReferenceScreenshots/ holds reference images, NOT copied into the built app. The SwiftUI views are original placeholders; no original UI or functionality is recovered.\n")
print("Generated",len(screens),"editable screens")
