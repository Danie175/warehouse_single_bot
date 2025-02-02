#! /usr/bin/env python3
# Copyright 2021 Samsung Research America
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
from copy import deepcopy
from geometry_msgs.msg import PoseStamped
from rclpy.duration import Duration
import rclpy
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

def parse_json(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
        
    machine_sequences = []
    ptime_sequences = []
    
    new_machine_sequences = []
    new_ptime_sequences = []
        
    for amr in data['amr_list']:
        machine_sequences.append(amr['machine_sequence'])
        ptime_sequences.append(amr['ptime_sequence'])
        
    for machines, ptimes in zip(machine_sequences, ptime_sequences):
        new_machines = []
        new_ptimes = []
        for machine, ptime in zip(machines, ptimes):
            if ptime != 0:
                new_machines.append(machine)
                new_ptimes.append(ptime)
        new_machine_sequences.append(new_machines)
        new_ptime_sequences.append(new_ptimes)
    
    print(machine_sequences, ptime_sequences)
    print(new_machine_sequences, new_ptime_sequences)
    amr1_sequence = new_machine_sequences[0]
    amr1_ptimes = new_ptime_sequences[0]
    return amr1_sequence, amr1_ptimes

class JSONFileHandler(FileSystemEventHandler):
    def __init__(self, file_path, callback):
        self.file_path = file_path
        self.callback = callback
        self.callback_called = False

    def on_modified(self, event):
        if event.src_path == self.file_path and not self.callback_called:
            with open(self.file_path, 'r') as file:
                data = json.load(file)
            self.callback(data)
            self.callback_called = True

def wait_for_json_update(file_path, callback):
    event_handler = JSONFileHandler(file_path, callback)
    observer = Observer()
    observer.schedule(event_handler, path=file_path, recursive=False)
    observer.start()

    try:
        while not event_handler.callback_called:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.stop()
    observer.join()

def on_json_update(data):
    print("JSON file updated with new values:")
    print(data)
    start_execution(data)

def start_execution(data):
    rclpy.init()

    navigator = BasicNavigator()

    m1 = [-3.37, 6.62]
    m2 = [-3.47, 1.057]
    m3 = [1.78, 6.6]
    m4 = [1.69, 1.44]
    loading_dock = [-6.83, 4.05]
    unloading_dock = [3.66, 4.05]

    poses = {
        '0': m1,
        '1': m2,
        '2': m3,
        '3': m4,
        '-1': loading_dock,
        '-2': unloading_dock
    }

    inspection_route = []
    json_file_path = '/home/tarun_56/lmas_ws/src/JobShopGA/amr_data.json'
    sequence, ptimes = parse_json(json_file_path)

    for m in sequence:
        inspection_route.append(poses[str(m)])

    for i,m in zip(range(len(sequence)),sequence):
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = poses[str(m)][0]
        goal_pose.pose.position.y = poses[str(m)][1]
        goal_pose.pose.orientation.w = 1.0

        navigator.goToPose(goal_pose)
        if m >= 0:
            print(f'Going to machine {m}')
        elif m == -1:
            print('Going to Loading dock for next job')
        elif m == -2:
            print('Going to unloading dock to drop completed job')
        while not navigator.isTaskComplete():
            time.sleep(1)
        
        print(f'job being process for time {ptimes[i]} seconds')
        time.sleep(ptimes[i])

    result = navigator.getResult()
    if result == TaskResult.SUCCEEDED:
        print('Inspection of shelves complete! Returning to start...')
    elif result == TaskResult.CANCELED:
        print('Inspection of shelving was canceled. Returning to start...')
        exit(1)
    elif result == TaskResult.FAILED:
        print('Inspection of shelving failed! Returning to start...')

def main():
    print('go to points is being executed')
    json_file_path = '/home/tarun_56/lmas_ws/src/JobShopGA/amr_data.json'
    wait_for_json_update(json_file_path, on_json_update)

if __name__ == '__main__':
    main()
