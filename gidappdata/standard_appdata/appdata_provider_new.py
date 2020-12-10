# region [Imports]


import lzma
import os
from dotenv import load_dotenv
import zipfile
import os
import base64

import gidlogger as glog
from gidconfig.standard import ConfigHandler

from gidappdata.standard_appdata.appdata_storager import AppDataStorager
from gidappdata.utility.functions import pathmaker, to_attr_name, filename_to_attr_name, create_folder, create_file
from gidappdata.utility.extended_dotenv import find_dotenv_everywhere
from gidappdata.utility.exceptions import ConstructionEnvDataMissing, DevSettingError
# endregion [Imports]

__updated__ = '2020-12-01 04:22:55'

# region [Logging]

log = glog.aux_logger(__name__)
log.info(glog.imported(__name__))

# endregion [Logging]


class SupportKeeperMetaHelper(type):
    def __getattr__(cls, name):
        _out = SupportKeeper.configs.get(name, None)
        if _out is None:
            _out = SupportKeeper.app_info.get(name)
        if _out is None:
            raise AttributeError
        return _out


class SupportKeeper(metaclass=SupportKeeperMetaHelper):
    # region [ClassAttributes]

    is_init = False
    appdata = None
    configs = {}
    construction_env_filename = 'construction_info.env'
    app_info = {'app_name': None, 'author_name': None, 'uses_base64': None, 'clean': True, 'dev': False, 'redirect': ''}
    config_handler = ConfigHandler

    # endregion[ClassAttributes]
    @staticmethod
    def _unzip(root_dir, zip_file, overwrite: bool = False):
        # sourcery skip: simplify-boolean-comparison
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            for item in zipf.namelist():
                _info = zipf.getinfo(item)
                if _info.is_dir() is True:
                    create_folder(pathmaker(root_dir, item))
                else:
                    if os.path.isfile(pathmaker(root_dir, item)) is False or overwrite is True:
                        zipf.extract(item, pathmaker(root_dir))
                        log.debug("extracted file '%s' because it didn't exist", pathmaker(root_dir, item))
                    else:
                        log.debug("file '%s' is already existing and overwrite is 'False' so file was not extracted", pathmaker(root_dir, item))

    @classmethod
    def set_experimental_confighandler(cls):
        from gidconfig.experimental import GidAttConfigIni
        cls.config_handler = GidAttConfigIni

    @classmethod
    def set_clean(cls, setting: bool):
        cls.app_info['clean'] = setting

    @classmethod
    def set_dev(cls, setting: bool, redirect=None):
        # sourcery skip: simplify-boolean-comparison
        cls.app_info['dev'] = setting
        if setting is True:
            if redirect is None:
                raise DevSettingError()
            cls.app_info['redirect'] = pathmaker(redirect)

    @staticmethod
    def checked_get_env(env_var_name):
        _out = os.getenv(env_var_name)
        if _out is None:
            raise ConstructionEnvDataMissing(env_var_name)
        if _out.casefold() in ['true', 'yes', '1']:
            _out = True
        elif _out.casefold() in ['false', 'no', '0']:
            _out = False
        else:
            _out = _out
        return _out

    @classmethod
    def _archive_from_bin(cls, bin_data, name: str = 'user_data_archive', ext: str = 'zip', uses_base64: bool = False):
        _file = pathmaker(str(cls.appdata), name + '.' + ext)
        with open(_file, 'wb') as archfile:
            _bin_data = bin_data if not uses_base64 else base64.b64decode(bin_data)
            archfile.write(_bin_data)
        return _file

    @classmethod
    def unpack_archive(cls, in_archive, clean: bool, uses_base64: bool):
        _file = cls._archive_from_bin(in_archive, uses_base64=uses_base64)
        cls._unzip(str(cls.appdata), _file, False)
        if clean:
            os.remove(_file)

    @classmethod
    def initialize(cls, archive_data):
        if cls.is_init is True:
            return
        load_dotenv(find_dotenv_everywhere(cls.construction_env_filename))
        for info in cls.app_info:
            if cls.app_info[info] is None:
                cls.app_info[info] = cls.checked_get_env(info.upper())
        redirect = None if cls.app_info['redirect'] == '' else cls.app_info['redirect']
        cls.appdata = AppDataStorager(cls.app_info['author_name'], cls.app_info['app_name'], cls.app_info['dev'], redirect)
        cls.unpack_archive(archive_data, cls.app_info['clean'], cls.app_info['uses_base64'])
        if os.path.isdir(cls.appdata['config']) is True:
            for file in os.scandir(cls.appdata['config']):
                if file.name.endswith('.ini') and 'config' in file.name:
                    name = filename_to_attr_name(file.name)
                    cls.configs[name] = ConfigHandler(cls.appdata[file.name])


if __name__ == '__main__':
    pass