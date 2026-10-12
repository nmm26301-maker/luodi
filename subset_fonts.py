"""Optional asset regeneration from official Noto Sans CJK SC OTF files.
Requires fontTools. Pass the directory containing Regular and Bold OTFs.
Renames the modified fonts to Luodi UI according to the bundled OFL.
"""
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
import re, sys
ROOT=Path(__file__).resolve().parent
assets=ROOT/'app/src/main/assets'
source=Path(sys.argv[1])
text=''.join((assets/n).read_text() for n in ['app.js','care.js','care-data.js','index.html','styles.css'])
chars=set(text)|set(chr(n) for n in range(32,127))
ranges=','.join('U+%X'%ord(c) for c in sorted(chars))
for style,weight in [('Regular',400),('Bold',700)]:
 font=TTFont(source/f'NotoSansCJKsc-{style}.otf')
 opt=subset.Options();opt.layout_features=['*']
 sub=subset.Subsetter(options=opt);sub.populate(text=''.join(chars));sub.subset(font)
 for row in font['name'].names:
  if row.nameID in {1,2,3,4,6,16,17}:
   value={1:'Luodi UI',2:style,3:f'LuodiUI-{style}',4:f'Luodi UI {style}',6:f'LuodiUI-{style}',16:'Luodi UI',17:style}[row.nameID]
   row.string=value.encode(row.getEncoding())
 font.flavor='woff';font.save(assets/'vendor'/f'LuodiUI-{style}.woff')
css=(assets/'styles.css').read_text()
css=re.sub(r'@font-face\{[^}]*\}', '',css)
css+='\n'+''.join(f'@font-face{{font-family:LuodiUI;src:url(vendor/LuodiUI-{style}.woff) format("woff");font-weight:{weight};font-display:swap;unicode-range:{ranges}}}\n' for style,weight in [('Regular',400),('Bold',700)])
(assets/'styles.css').write_text(css)
