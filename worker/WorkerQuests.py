import math
import os
import time
from enum import Enum
from threading import Event, Thread

from utils.geo import (
    get_distance_of_two_points_in_meters,
    get_lat_lng_offsets_by_distance
)
from utils.logging import logger
from utils.madGlobals import (
    InternalStopWorkerException,
    WebsocketWorkerRemovedException
)
from worker.MITMBase import MITMBase, LatestReceivedType


class FortSearchResultTypes(Enum):
    UNDEFINED = 0
    QUEST = 1
    TIME = 2
    COOLDOWN = 3
    INVENTORY = 4
    LIMIT = 5
    UNAVAILABLE = 6
    OUT_OF_RANGE = 7


class WorkerQuests(MITMBase):
    def _valid_modes(self):
        return ["pokestops"]

    def __init__(self, args, id, last_known_state, websocket_handler, walker_routemanager,
                 mitm_mapper, devicesettings, db_wrapper, pogoWindowManager, walker):
        MITMBase.__init__(self, args, id, last_known_state, websocket_handler,
                          walker_routemanager, devicesettings, db_wrapper=db_wrapper, NoOcr=False,
                          mitm_mapper=mitm_mapper, pogoWindowManager=pogoWindowManager, walker=walker)

        self.clear_thread = None
        # 0 => None
        # 1 => clear box
        # 2 => clear quest
        self.clear_thread_task = 0
        self._start_inventory_clear = Event()
        self._delay_add = int(self._devicesettings.get("vps_delay", 0))
        self._stop_process_time = 0

    def _pre_work_loop(self):
        if self.clear_thread is not None:
            return
        self.clear_thread = Thread(name="clear_thread_%s" % str(
                self._id), target=self._clear_thread)
        self.clear_thread.daemon = False
        self.clear_thread.start()
        self._get_screen_size()

        reached_main_menu = self._check_pogo_main_screen(10, True)
        if not reached_main_menu:
            if not self._restart_pogo():
                # TODO: put in loop, count up for a reboot ;)
                raise InternalStopWorkerException

    def _health_check(self):
        """
        Not gonna check for main screen here since we will do health checks in post_move_location_routine
        :return:
        """
        pass

    def _pre_location_update(self):
        self._start_inventory_clear.set()
        self._update_injection_settings()

    def _move_to_location(self):
        routemanager = self._walker_routemanager
        if routemanager is None:
            raise InternalStopWorkerException
        if self._db_wrapper.check_stop_quest(self.current_location.lat, self.current_location.lng):
            return False, False

        distance = get_distance_of_two_points_in_meters(float(self.last_location.lat),
                                                        float(
                                                                self.last_location.lng),
                                                        float(
                                                                self.current_location.lat),
                                                        float(self.current_location.lng))
        logger.debug('Moving {} meters to the next position', round(distance, 2))

        delay_used = 0
        logger.debug("Getting time")
        speed = routemanager.settings.get("speed", 0)
        max_distance = routemanager.settings.get("max_distance", None)
        if (speed == 0 or
                (max_distance and 0 < max_distance < distance)
                or (self.last_location.lat == 0.0 and self.last_location.lng == 0.0)):
            logger.debug("main: Teleporting...")
            self._transporttype = 0
            self._communicator.setLocation(
                    self.current_location.lat, self.current_location.lng, 0)
            # the time we will take as a starting point to wait for data...
            cur_time = math.floor(time.time())

            delay_used = self._devicesettings.get('post_teleport_delay', 7)
            speed = 16.67  # Speed can be 60 km/h up to distances of 3km

            if self.last_location.lat == 0.0 and self.last_location.lng == 0.0:
                logger.info('Starting fresh round - using lower delay')
                delay_used = self._devicesettings.get('post_teleport_delay', 7)
            else:
                if distance >= 1335000:
                    speed = 180.43  # Speed can be abt 650 km/h
                elif distance >= 1100000:
                    speed = 176.2820513
                elif distance >= 1020000:
                    speed = 168.3168317
                elif distance >= 1007000:
                    speed = 171.2585034
                elif distance >= 948000:
                    speed = 166.3157895
                elif distance >= 900000:
                    speed = 164.8351648
                elif distance >= 897000:
                    speed = 166.1111111
                elif distance >= 839000:
                    speed = 158.9015152
                elif distance >= 802000:
                    speed = 159.1269841
                elif distance >= 751000:
                    speed = 152.6422764
                elif distance >= 700000:
                    speed = 151.5151515
                elif distance >= 650000:
                    speed = 146.3963964
                elif distance >= 600000:
                    speed = 142.8571429
                elif distance >= 550000:
                    speed = 138.8888889
                elif distance >= 500000:
                    speed = 134.4086022
                elif distance >= 450000:
                    speed = 129.3103448
                elif distance >= 400000:
                    speed = 123.4567901
                elif distance >= 350000:
                    speed = 116.6666667
                elif distance >= 328000:
                    speed = 113.8888889
                elif distance >= 300000:
                    speed = 108.6956522
                elif distance >= 250000:
                    speed = 101.6260163
                elif distance >= 201000:
                    speed = 90.54054054
                elif distance >= 175000:
                    speed = 85.78431373
                elif distance >= 150000:
                    speed = 78.125
                elif distance >= 125000:
                    speed = 71.83908046
                elif distance >= 100000:
                    speed = 64.1025641
                elif distance >= 90000:
                    speed = 60
                elif distance >= 80000:
                    speed = 55.55555556
                elif distance >= 70000:
                    speed = 50.72463768
                elif distance >= 60000:
                    speed = 47.61904762
                elif distance >= 45000:
                    speed = 39.47368421
                elif distance >= 40000:
                    speed = 35.0877193
                elif distance >= 35000:
                    speed = 32.40740741
                elif distance >= 30000:
                    speed = 29.41176471
                elif distance >= 25000:
                    speed = 27.77777778
                elif distance >= 20000:
                    speed = 27.77777778
                elif distance >= 15000:
                    speed = 27.77777778
                elif distance >= 10000:
                    speed = 23.80952381
                elif distance >= 8000:
                    speed = 26.66666667
                elif distance >= 5000:
                    speed = 22.34137623
                elif distance >= 4000:
                    speed = 22.22222222

                delay_used = distance / speed

                if delay_used > 7200:  # There's a maximum of 2 hours wait time
                    delay_used = 7200
            logger.debug(
                    "Need more sleep after Teleport: {} seconds!", str(delay_used))
        else:
            logger.info("main: Walking...")
            self._transporttype = 1
            self._communicator.walkFromTo(self.last_location.lat, self.last_location.lng,
                                          self.current_location.lat,
                                          self.current_location.lng, speed)
            # the time we will take as a starting point to wait for data...
            cur_time = math.floor(time.time())
            delay_used = self._devicesettings.get('post_walk_delay', 7)

        walk_distance_post_teleport = self._devicesettings.get(
                'walk_after_teleport_distance', 0)
        if 0 < walk_distance_post_teleport < distance:
            # TODO: actually use to_walk for distance
            lat_offset, lng_offset = get_lat_lng_offsets_by_distance(
                    walk_distance_post_teleport)

            to_walk = get_distance_of_two_points_in_meters(float(self.current_location.lat),
                                                           float(
                                                                   self.current_location.lng),
                                                           float(
                                                                   self.current_location.lat) + lat_offset,
                                                           float(self.current_location.lng) + lng_offset)
            logger.info("Walking roughly: {}", str(to_walk))
            time.sleep(0.3)
            self._communicator.walkFromTo(self.current_location.lat,
                                          self.current_location.lng,
                                          self.current_location.lat + lat_offset,
                                          self.current_location.lng + lng_offset,
                                          11)
            logger.debug("Walking back")
            time.sleep(0.3)
            self._communicator.walkFromTo(self.current_location.lat + lat_offset,
                                          self.current_location.lng + lng_offset,
                                          self.current_location.lat,
                                          self.current_location.lng,
                                          11)
            logger.debug("Done walking")
            time.sleep(1)
            delay_used -= (to_walk / 3.05) - 1.  # We already waited for a bit because of this walking part
            if delay_used < 0:
                delay_used = 0

        if self._init:
            delay_used = 5

        if self._devicesettings.get('last_action_time', None) is not None:
            timediff = time.time() - self._devicesettings['last_action_time']
            logger.info(
                    "Timediff between now and last action time: {}", str(float(timediff)))
            delay_used = delay_used - timediff
        else:
            logger.debug("No last action time found - no calculation")

        if delay_used < 0:
            logger.info('No more cooldowntime - start over')
        else:
            logger.info("Real sleep time: {} seconds!", str(delay_used))
            cleanupbox = False
            lastcleanupbox = self._devicesettings.get(
                    'last_cleanup_time', None)
            if lastcleanupbox is not None:
                if time.time() - lastcleanupbox > 900:
                    # just cleanup if last cleanup time > 15 minutes ago
                    cleanupbox = True
            while time.time() <= int(cur_time) + int(delay_used):
                if delay_used > 200 and cleanupbox:
                    self.clear_thread_task = 1
                    cleanupbox = False
                time.sleep(1)

        self._devicesettings["last_location"] = self.current_location
        self.last_location = self.current_location
        return cur_time, True

    def _post_move_location_routine(self, timestamp: float):
        if self._stop_worker_event.is_set():
            raise InternalStopWorkerException
        self._work_mutex.acquire()
        if not self._walker_routemanager.init:
            logger.info("Processing Stop / Quest...")

            reachedMainMenu = self._check_pogo_main_screen(10, False)
            if not reachedMainMenu:
                self._restart_pogo()

            logger.info('Open Stop')

            data_received = self._open_pokestop(timestamp)
            if data_received is not None and data_received == LatestReceivedType.STOP:
                self._handle_stop(timestamp)
        else:
            logger.info('Currently in INIT Mode - no Stop processing')
        logger.debug("Releasing lock")
        self._work_mutex.release()

    def _start_pogo(self):
        pogo_topmost = self._communicator.isPogoTopmost()
        if pogo_topmost:
            return True

        if not self._communicator.isScreenOn():
            # TODO
            self._communicator.startApp("de.grennith.rgc.remotegpscontroller")
            logger.warning("Turning screen on")
            self._communicator.turnScreenOn()
            time.sleep(self._devicesettings.get(
                    "post_turn_screen_on_delay", 7))

        cur_time = time.time()
        start_result = False
        while not pogo_topmost:
            self._mitm_mapper.set_injection_status(self._id, False)
            start_result = self._communicator.startApp(
                    "com.nianticlabs.pokemongo")
            time.sleep(1)
            pogo_topmost = self._communicator.isPogoTopmost()
        reached_raidtab = False
        if start_result:
            logger.warning("startPogo: Starting pogo...")
            self._last_known_state["lastPogoRestart"] = cur_time
            reached_mainscreen = True
        return reached_mainscreen

    def _cleanup(self):
        if self.clear_thread is not None:
            self.clear_thread.join()

    def _clear_thread(self):
        logger.info('Starting clear Quest Thread')
        while not self._stop_worker_event.is_set():
            # wait for event signal
            while not self._start_inventory_clear.is_set():
                if self._stop_worker_event.is_set():
                    return
                time.sleep(0.5)
            if self.clear_thread_task > 0:
                self._work_mutex.acquire()
                try:
                    # TODO: less magic numbers?
                    time.sleep(1)
                    if self.clear_thread_task == 1:
                        logger.info("Clearing box")
                        self.clear_box(self._delay_add)
                        self.clear_thread_task = 0
                        self._devicesettings['last_cleanup_time'] = time.time()
                    elif self.clear_thread_task == 2:
                        logger.info("Clearing quest")
                        self._clear_quests(self._delay_add)
                        self.clear_thread_task = 0
                    time.sleep(1)
                    self._start_inventory_clear.clear()
                except WebsocketWorkerRemovedException as e:
                    logger.error("Worker removed while clearing quest/box")
                    self._stop_worker_event.set()
                    return
                self._work_mutex.release()

    def clear_box(self, delayadd):
        stop_inventory_clear = Event()
        stop_screen_clear = Event()
        logger.info('Cleanup Box')
        not_allow = ('Gift', 'Geschenk', 'Glücksei', 'Lucky Egg', 'FrenchNameForLuckyEgg',
                     'Cadeau', 'Appareil photo', 'Wunderbox', 'Mystery Box', 'Boîte Mystère')
        x, y = self._resocalc.get_close_main_button_coords(self)[0], self._resocalc.get_close_main_button_coords(self)[
            1]
        self._communicator.click(int(x), int(y))
        time.sleep(1 + int(delayadd))
        x, y = self._resocalc.get_item_menu_coords(
                self)[0], self._resocalc.get_item_menu_coords(self)[1]
        self._communicator.click(int(x), int(y))
        time.sleep(2 + int(delayadd))
        _data_err_counter = 0
        _pos = 1
        text_x1, text_x2, text_y1, text_y2 = self._resocalc.get_delete_item_text(
                self)
        x, y = self._resocalc.get_delete_item_coords(
                self)[0], self._resocalc.get_delete_item_coords(self)[1]
        click_x1, click_x2, click_y = self._resocalc.get_swipe_item_amount(self)[0], \
                                      self._resocalc.get_swipe_item_amount(self)[1], \
                                      self._resocalc.get_swipe_item_amount(self)[2]
        delrounds = 0
        first_round = True
        delete_allowed = False
        error_counter = 0

        while int(delrounds) <= 8 and not stop_inventory_clear.is_set():

            trash = 0
            if not first_round and not delete_allowed:
                error_counter += 1
                if error_counter > 3:
                    stop_inventory_clear.set()
                logger.warning('Find no item to delete: {}', str(error_counter))
                self._communicator.touchandhold(int(200), int(300), int(200), int(100))
                time.sleep(2)

            trashcancheck = self._get_trash_positions()
            if trashcancheck is None:
                logger.error('Could not find any trashcan - abort')
                return
            logger.info("Found {} trashcan(s) on screen", len(trashcancheck))
            first_round = False
            delete_allowed = False
            stop_screen_clear.clear()

            while int(trash) <= len(trashcancheck) - 1 and not stop_screen_clear.is_set():
                check_y_text_starter = int(trashcancheck[trash].y)
                check_y_text_ending = int(trashcancheck[trash].y) + self._resocalc.get_inventory_text_diff(self)

                try:
                    item_text = self._pogoWindowManager.get_inventory_text(self.get_screenshot_path(),
                                                                       self._id, text_x1, text_x2, check_y_text_ending,
                                                                       check_y_text_starter)

                    logger.info("Found item {}", str(item_text))
                    if item_text in not_allow:
                        logger.info('Could not delete this item - check next one')
                        trash += 1
                    else:
                        logger.info('Could delete this item')
                        self._communicator.click(int(trashcancheck[trash].x), int(trashcancheck[trash].y))
                        time.sleep(1 + int(delayadd))

                        self._communicator.touchandhold(
                            click_x1, click_y, click_x2, click_y)
                        time.sleep(1)

                        delx, dely = self._resocalc.get_confirm_delete_item_coords(self)[0], \
                                     self._resocalc.get_confirm_delete_item_coords(self)[1]
                        curTime = time.time()
                        self._communicator.click(int(delx), int(dely))

                        data_received = self._wait_for_data(
                            timestamp=curTime, proto_to_wait_for=4, timeout=35)

                        if data_received is not None:
                            if data_received == LatestReceivedType.CLEAR:
                                delrounds += 1
                                stop_screen_clear.set()
                                delete_allowed = True
                        else:
                            logger.error('Unknown error clearing out {}', str(item_text))
                            stop_screen_clear.set()
                            stop_inventory_clear.set()

                except UnicodeEncodeError as e:
                    logger.warning('Found some text that was not unicode!')
                    stop_inventory_clear.set()
                    stop_screen_clear.set()
                    pass

        x, y = self._resocalc.get_close_main_button_coords(self)[0], self._resocalc.get_close_main_button_coords(self)[
            1]
        self._communicator.click(int(x), int(y))
        time.sleep(1 + int(delayadd))
        return True

    def _update_injection_settings(self):
        injected_settings = {}
        scanmode = "quests"
        injected_settings["scanmode"] = scanmode
        ids_iv = self._walker_routemanager.settings.get("mon_ids_iv", None)
        # if iv ids are specified we will sync the workers encountered ids to newest time.
        if ids_iv:
            (self._latest_encounter_update, encounter_ids) = self._db_wrapper.update_encounters_from_db(
                    self._walker_routemanager.geofence_helper, self._latest_encounter_update)
            if encounter_ids:
                logger.debug("Found {} new encounter_ids", len(encounter_ids))
                for encounter_id, disappear in encounter_ids.items():
                    logger.debug("id: {}, despawn: {}",
                                 encounter_id, disappear)
            self._encounter_ids = {**encounter_ids, **self._encounter_ids}
            # allow one minute extra life time, because the clock on some devices differs, newer got why this problem
            # apears but it is a fact.
            max_age = time.time() - 60

            remove = []
            for key, value in self._encounter_ids.items():
                if value < max_age:
                    remove.append(key)
                    logger.debug("removing encounterid: {} mon despawned", key)

            for key in remove:
                del self._encounter_ids[key]

            logger.debug("Encounter list len: {}", len(self._encounter_ids))
            # TODO: here we have the latest update of encountered mons.
            # self._encounter_ids contains the complete dict.
            # encounter_ids only contains the newest update.
        self._mitm_mapper.update_latest(origin=self._id, timestamp=int(time.time()), key="ids_encountered",
                                        values_dict=self._encounter_ids)
        self._mitm_mapper.update_latest(origin=self._id, timestamp=int(time.time()), key="ids_iv",
                                        values_dict=ids_iv)

        self._mitm_mapper.update_latest(origin=self._id, timestamp=int(time.time()), key="injected_settings",
                                        values_dict=injected_settings)

    def _current_position_has_spinnable_stop(self, timestamp: float):
        latest: dict = self._mitm_mapper.request_latest(self._id)
        if latest is None or 106 not in latest.keys():
            return False

        gmo_cells: list = latest.get(106).get("values", {}).get("payload", {}).get("cells", None)
        if gmo_cells is None:
            return False
        for cell in gmo_cells:
            # each cell contains an array of forts, check each cell for a fort with our current location (maybe +-
            # very very little jitter) and check its properties
            forts: list = cell.get("forts", None)
            if forts is None:
                continue

            for fort in forts:
                latitude: float = fort.get("latitude", 0.0)
                longitude: float = fort.get("longitude", 0.0)
                if latitude == 0.0 or longitude == 0.0:
                    continue
                elif (abs(self.current_location.lat - latitude) > 0.00003 or
                      abs(self.current_location.lng - longitude) > 0.00003):
                    continue

                fort_type: int = fort.get("type", 0)
                if fort_type == 0:
                    self._db_wrapper.delete_stop(latitude, longitude)
                    return False
                enabled: bool = fort.get("enabled", True)
                closed: bool = fort.get("closed", False)
                cooldown: int = fort.get("cooldown_complete_ms", 0)
                return fort_type == 1 and enabled and not closed and cooldown == 0
        # by now we should've found the stop in the GMO
        # TODO: consider counter in DB for stop and delete if N reached, reset when updating with GMO
        return False

    def _open_pokestop(self, timestamp: float):
        to = 0
        data_received = LatestReceivedType.UNDEFINED

        # let's first check the GMO for the stop we intend to visit and abort if it's disabled, a gym, whatsoever
        if not self._current_position_has_spinnable_stop(timestamp):
            # wait for GMO in case we moved too far away
            data_received = self._wait_for_data(
                    timestamp=timestamp, proto_to_wait_for=106, timeout=25)
            if data_received == LatestReceivedType.UNDEFINED and not self._current_position_has_spinnable_stop(timestamp):
                logger.info("Stop {} considered to be ignored in the next round due to failed spinnable check")
                self._walker_routemanager.add_coord_to_be_removed(self.current_location.lat, self.current_location.lng)
                return None
        while data_received != LatestReceivedType.STOP and int(to) < 3:
            self._stop_process_time = math.floor(time.time())
            self._waittime_without_delays = self._stop_process_time
            self._open_gym(self._delay_add)
            data_received = self._wait_for_data(
                    timestamp=self._stop_process_time, proto_to_wait_for=104, timeout=25)
            if data_received == LatestReceivedType.GYM:
                logger.info('Clicking GYM')
                time.sleep(1)
                x, y = (self._resocalc.get_close_main_button_coords(self)[0],
                        self._resocalc.get_close_main_button_coords(self)[1])
                self._communicator.click(int(x), int(y))
                time.sleep(1)
                if not self._checkPogoButton():
                    self._checkPogoClose()
                self._turn_map(self._delay_add)
            elif data_received == LatestReceivedType.MON:
                time.sleep(1)
                logger.info('Clicking MON')
                time.sleep(.5)
                self._turn_map(self._delay_add)
            elif data_received == LatestReceivedType.UNDEFINED:
                if not self._checkPogoButton():
                    self._checkPogoClose()

            to += 1
        return data_received

    # TODO: handle https://github.com/Furtif/POGOProtos/blob/master/src/POGOProtos/Networking/Responses
    #  /FortSearchResponse.proto#L12
    def _handle_stop(self, timestamp: float):
        to = 0
        data_received = FortSearchResultTypes.UNDEFINED
        while data_received != FortSearchResultTypes.QUEST and int(to) < 4:
            logger.info('Spin Stop')
            data_received = self._wait_for_data(
                timestamp=self._stop_process_time, proto_to_wait_for=101, timeout=25)
            if data_received == FortSearchResultTypes.INVENTORY:
                logger.error('Box is full ... Next round!')
                self.clear_thread_task = 1
                break
            elif data_received == FortSearchResultTypes.QUEST or data_received == FortSearchResultTypes.COOLDOWN:
                logger.info('Received new Quest or have previously spun the stop')
                self.clear_thread_task = 2
                break
            elif (data_received == FortSearchResultTypes.TIME or data_received ==
                  FortSearchResultTypes.OUT_OF_RANGE):
                logger.error('Softban - waiting...')
                time.sleep(10)
                if self._open_pokestop(timestamp) is None:
                    self._devicesettings['last_action_time'] = time.time()
                    return
            else:
                logger.info("Likely already spun this stop or brief softban, trying again")
                if to > 2 and self._db_wrapper.check_stop_quest(self.current_location.lat, self.current_location.lng):
                    logger.info('Quest is done without us noticing. Getting new Quest...')
                    self.clear_thread_task = 2
                    break
                self._close_gym(self._delay_add)

                self._turn_map(self._delay_add)
                time.sleep(1)
                if self._open_pokestop(timestamp) is None:
                    self._devicesettings['last_action_time'] = time.time()
                    return
                to += 1

        self._devicesettings['last_action_time'] = time.time()

    def _wait_data_worker(self, latest, proto_to_wait_for, timestamp):
        if latest is None:
            logger.debug("Nothing received since MAD started")
            time.sleep(0.5)
        elif proto_to_wait_for not in latest:
            logger.debug(
                    "No data linked to the requested proto since MAD started.")
            time.sleep(0.5)
        elif 156 in latest and latest[156].get('timestamp', 0) >= timestamp:
            return LatestReceivedType.GYM
        elif 102 in latest and latest[102].get('timestamp', 0) >= timestamp:
            return LatestReceivedType.MON
        else:
            # proto has previously been received, let's check the timestamp...
            # TODO: int vs str-key?
            latest_proto = latest.get(proto_to_wait_for, None)
            latest_timestamp = latest_proto.get("timestamp", 0)
            if latest_timestamp >= timestamp:
                # TODO: consider reseting timestamp here since we clearly received SOMETHING
                latest_data = latest_proto.get("values", None)
                if latest_data is None:
                    time.sleep(0.5)
                    return None
                elif proto_to_wait_for == 101:
                    payload: dict = latest_data.get("payload", None)
                    if payload is None:
                        return None
                    result: int = latest_data.get("payload", {}).get("result", 0)
                    if result == 1 and len(payload.get('items_awarded', [])) > 0:
                        return FortSearchResultTypes.QUEST
                    elif (result == 1
                          and len(payload.get('items_awarded', [])) == 0):
                        return FortSearchResultTypes.TIME
                    elif result == 2:
                        return FortSearchResultTypes.OUT_OF_RANGE
                    elif result == 4:
                        return FortSearchResultTypes.INVENTORY
                    elif result == 3:
                        return FortSearchResultTypes.COOLDOWN
                elif proto_to_wait_for == 104:
                    fort_type: int = latest_data.get("payload").get("type", 0)
                    if fort_type == 0:
                        return LatestReceivedType.GYM
                    else:
                        return LatestReceivedType.STOP
                if proto_to_wait_for == 4 and len(latest_data['payload']['inventory_delta']['inventory_items']) > 0:
                    return LatestReceivedType.CLEAR
            else:
                logger.debug("latest timestamp of proto {} ({}) is older than {}", str(
                        proto_to_wait_for), str(latest_timestamp), str(timestamp))
                # TODO: timeoutopen error instead of data_error_counter? Differentiate timeout vs missing data (the
                # TODO: latter indicates too high speeds for example
                time.sleep(0.5)
        return LatestReceivedType.UNDEFINED
