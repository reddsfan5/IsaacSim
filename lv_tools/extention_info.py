
import omni
def get_extention_path(extention_python_path='omni.replicator.core'):

    manager = omni.kit.app.get_app().get_extension_manager()


    # there could be multiple extensions with same name, but different version
    # many functions accept extension id: [ext name]-[ext version].
    # you can get the extension by name or by python module name:
    ext_id = manager.get_enabled_extension_id(extention_python_path)
    # or
    ext_id = manager.get_extension_id_by_module(extention_python_path)

    # there are few ways to get file path to a extension:
    print(manager.get_extension_path(ext_id))
    print(manager.get_extension_dict(ext_id)["path"])
    print(manager.get_extension_path_by_module(extention_python_path))

get_extention_path()


