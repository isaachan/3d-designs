"""Instrument a copy of the text generator; leave production source unchanged."""
import subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent
SOURCE=OUT.parents[1]/'bambu-print/generate-label-mask.swift'
extra='''
FileHandle.standardError.write(Data("width=\\(bitmap.pixelsWide), height=\\(bitmap.pixelsHigh), bytesPerRow=\\(bitmap.bytesPerRow), samplesPerPixel=\\(bitmap.samplesPerPixel)\\n".utf8))
try! bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "OUTDIR/raw-\\(vertical ? "vertical" : "horizontal").png"))
'''.replace('OUTDIR',str(OUT))
code=SOURCE.read_text().replace('let bytes = bitmap.bitmapData!',extra+'\nlet bytes = bitmap.bitmapData!')
(OUT/'instrumented-label.swift').write_text(code)
for name,text,size,w,h,orientation in [('vertical','BOOK DEPOT','16','36','180','vertical'),('horizontal',"Lovely Car I've Driven",'30','440','64','horizontal')]:
    result=subprocess.run(['/usr/bin/swift',str(OUT/'instrumented-label.swift'),text,size,w,h,orientation],capture_output=True,text=True,check=True)
    (OUT/f'{name}-mask.json').write_text(result.stdout)
    print(name,result.stderr.strip())
