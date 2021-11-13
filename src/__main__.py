"""
This file allows running the parent directory directly:
python3 src [ arg1 ... ]

This also allows packaging up as a zipapp.

If you do not need this functionality:
  - Remove this file.
  - Consider moving scholaremailstocsv out of src.
"""

import scholaremailstocsv.__main__

scholaremailstocsv.__main__.main()
