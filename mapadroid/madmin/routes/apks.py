import io
import json

import werkzeug.exceptions
from flask import Response, flash, redirect, render_template, request, url_for

from mapadroid.mad_apk import (MAD_APKS, AbstractAPKStorage, APK_Arch,
                               APK_Type, MAD_Package, MAD_Packages,
                               PackageImporter, get_apk_status,
                               is_newer_version, lookup_apk_enum,
                               lookup_arch_enum, parse_frontend)
from mapadroid.madmin.functions import auth_required
from mapadroid.utils import MappingManager, global_variables
from mapadroid.utils.logging import logger


class apk_manager(object):
    def __init__(self, db, args, app, mapping_manager: MappingManager, deviceUpdater, storage_obj: AbstractAPKStorage):
        self._db = db
        self._args = args
        self._app = app
        self._mapping_manager = mapping_manager
        self._deviceUpdater = deviceUpdater
        self.storage_obj = storage_obj
        self.add_route()

    def add_route(self):
        routes = [
            ("/apk", self.mad_apks),
            ("/apk_update_status", self.apk_update_status),
        ]
        for route_def in routes:
            if len(route_def) == 2:
                route, view_func = route_def
                self._app.route(route)(view_func)
            elif len(route_def) == 3:
                route, view_func, methods = route_def
                self._app.route(route, methods=methods)(view_func)

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[
            1].lower() in global_variables.MAD_APK_ALLOWED_EXTENSIONS

    def apk_update_status(self):
        update_info = {}
        sql = "SELECT `usage`, `arch`, `version`, `download_status`, `last_checked`\n" \
              "FROM `mad_apk_autosearch`"
        autosearch_data = self._db.autofetch_all(sql)
        apk_info: MAD_APKS = get_apk_status(self.storage_obj)
        package: APK_Type = None
        arch: APK_Arch = None
        for row in autosearch_data:
            arch = lookup_arch_enum(row['arch'])
            package = lookup_apk_enum(row['usage'])
            composite_key = '%s_%s' % (row['usage'], row['arch'])
            update_info[composite_key] = {}
            if row['download_status'] != 0:
                update_info[composite_key]['download_status'] = row['download_status']
            try:
                curr_info = apk_info[package][arch]
            except KeyError:
                curr_info = None
            if package == APK_Type.pogo:
                if not curr_info or is_newer_version(row['version'], curr_info.version):
                    update_info[composite_key]['update'] = 1
            else:
                if curr_info is None or curr_info.size is None or row['version'] is None:
                    update_info[composite_key]['update'] = 1
                elif int(curr_info.size) != int(row['version']):
                    update_info[composite_key]['update'] = 1
            if not update_info[composite_key]:
                del update_info[composite_key]
        return Response(json.dumps(update_info), mimetype='application/json')

    @auth_required
    def mad_apks(self):
        return render_template('madmin_apk_root.html', apks=get_apk_status(self.storage_obj))
