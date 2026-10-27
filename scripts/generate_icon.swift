import AppKit
import Foundation

let output = CommandLine.arguments[1]
let n = 1024
let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: n, pixelsHigh: n, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
let rect = NSRect(x:0,y:0,width:n,height:n)
NSColor(calibratedRed:0.015,green:0.035,blue:0.085,alpha:1).setFill()
NSBezierPath(roundedRect:rect,xRadius:205,yRadius:205).fill()
let center = NSPoint(x:512,y:512)
for i in (0..<45).reversed() {
    let size = CGFloat(630+i*3)
    let ring = NSBezierPath(ovalIn:NSRect(x:center.x-size/2,y:center.y-size/2,width:size,height:size))
    ring.lineWidth = CGFloat(2 + (45-i)/4)
    NSColor(calibratedRed:0.05, green:0.48, blue:1, alpha:CGFloat(0.015+Double(45-i)/5000)).setStroke()
    ring.stroke()
}
let outer = NSBezierPath()
outer.move(to:NSPoint(x:512,y:860))
outer.line(to:NSPoint(x:860,y:235))
outer.line(to:NSPoint(x:165,y:235))
outer.close()
NSColor(calibratedRed:0.02,green:0.63,blue:1,alpha:1).setStroke()
outer.lineWidth=38
outer.lineJoinStyle = .round
outer.stroke()
let inner = NSBezierPath()
inner.move(to:NSPoint(x:512,y:720))
inner.line(to:NSPoint(x:674,y:340))
inner.line(to:NSPoint(x:350,y:340))
inner.close()
NSColor(calibratedRed:0.07,green:0.14,blue:0.3,alpha:1).setFill()
inner.fill()
inner.lineWidth = 12
NSColor(calibratedRed:0.45,green:0.87,blue:1,alpha:1).setStroke()
inner.stroke()
NSGraphicsContext.restoreGraphicsState()
try bitmap.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:output))
