from setuptools import setup, Extension

def main():
    setup(name="candump",
          version="1.0.1",
          description="Python interface for the fputs C library function",
          author="Baptiste Pestourie",
          author_email="baptiste.pestourie@advantics.fr",
          ext_modules=[Extension("candump", ["candump.c"])])

if __name__ == "__main__":
    main()
