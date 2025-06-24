from setuptools import setup

APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': None,  # Optionnel : tu peux mettre un chemin vers une icône .icns
    'packages': ['requests', 'PIL'],  # Modules utilisés dans ton app
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
