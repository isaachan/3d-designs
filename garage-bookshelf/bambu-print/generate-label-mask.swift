import AppKit

let arguments = CommandLine.arguments
guard arguments.count == 6,
      let parsedFontSize = Double(arguments[2]),
      let width = Int(arguments[3]),
      let height = Int(arguments[4]) else {
    fputs("用法：generate-label-mask.swift 文字 字号 宽 高\\n", stderr)
    exit(1)
}

let text = arguments[1]
let fontSize = CGFloat(parsedFontSize)
let vertical = arguments[5] == "vertical"
let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height,
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0
)!
let context = NSGraphicsContext(bitmapImageRep: bitmap)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = context
context.cgContext.setFillColor(NSColor.clear.cgColor)
context.cgContext.fill(CGRect(x: 0, y: 0, width: width, height: height))

// The labels are English. Helvetica Bold has complete Latin glyph coverage and
// stable metrics on macOS; the prior Chinese-first font produced cropped runs.
let font = NSFont(name: "Helvetica-Bold", size: fontSize) ?? NSFont.systemFont(ofSize: fontSize, weight: .bold)
let style = NSMutableParagraphStyle()
style.alignment = .center
let attributes: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: NSColor.white, .paragraphStyle: style]
if vertical {
    let charHeight = Int(fontSize * 1.05)
    for (index, character) in text.enumerated() {
        NSString(string: String(character)).draw(in: CGRect(x: 0, y: height - (index + 1) * charHeight, width: width, height: charHeight), withAttributes: attributes)
    }
} else {
    NSString(string: text).draw(in: CGRect(x: 0, y: 1, width: width, height: height), withAttributes: attributes)
}
NSGraphicsContext.restoreGraphicsState()

let bytes = bitmap.bitmapData!
var runs: [[Int]] = []
for y in 0..<height {
    var x = 0
    let rowStart = y * bitmap.bytesPerRow
    while x < width {
        while x < width && bytes[rowStart + x * 4 + 3] < 96 { x += 1 }
        let start = x
        while x < width && bytes[rowStart + x * 4 + 3] >= 96 { x += 1 }
        if x > start { runs.append([start, height - 1 - y, x - start]) }
    }
}
let data = try! JSONSerialization.data(withJSONObject: runs)
print(String(data: data, encoding: .utf8)!)
