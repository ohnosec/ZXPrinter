import os
import sys
import re
from datetime import datetime

print(f"Update importmap")

indexfilename = "src/index.html"
timestamp = datetime.today().strftime("%Y%m%d%H%M%S")

basepath = os.path.abspath(os.path.dirname(sys.argv[0])) # type: ignore

files = [file for file in os.listdir(f"{basepath}/src") if file.endswith(".js")]

template = r'''
    <script type="importmap">
      {{
        "imports": {{
          {imports}
        }}
      }}
    </script>'''

imports = ",\n          ".join([f'"./{file}": "./{file}?v={timestamp}"' for file in files])

importmap = template.format(imports=imports.lstrip()).lstrip()

with open(indexfilename, "r") as file:
    indexhtml = file.read()

indexhtml = re.sub(r'<script type="importmap">[\s\S]*?</script>', importmap, indexhtml, flags=re.MULTILINE)

with open(indexfilename, "w") as file:
    file.write(indexhtml)
