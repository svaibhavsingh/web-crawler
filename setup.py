from setuptools import setup

setup(name='web-crawler',
      version='1.0',
      author='Vaibhav Singh, Mrinal Aich',
      author_email='svaibhavsingh@gmail.com',
      packages=['crawler'],
      install_requires=['beautifulsoup4', 'goose3', 'requests'],
      zip_safe=False)
