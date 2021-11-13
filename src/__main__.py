"""
This file allows running the parent directory directly:
python3 src [ arg1 ... ]

This also allows packaging up as a zipapp.

If you do not need this functionality:
  - Remove this file.
  - Consider moving minimalhello out of src.
"""

import minimalhello.__main__

minimalhello.__main__.main()
