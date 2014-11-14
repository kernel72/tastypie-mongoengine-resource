from setuptools import setup

setup(
    name='tastypie-mongoengine-resource',
    version='0.1.0',
    py_modules=['tastypieMongoengineResource'],
    url='https://github.com/kernel72/tastypie-mongoengine-resource',
    license='https://github.com/kernel72/tastypie-mongoengine-resource/blob/master/LICENSE',
    author='kernel72',
    author_email='kernel72@list.ru',
    description='Basic resource for tastypie and mongoengine integration',
    install_requires=[
        'django-tastypie>=0.10.0',
        'mongoengine'
    ]
)
