import math
import os
import random
import sys
import time
from typing import List, Tuple

import tqdm
import yaml


class Config:
    def __init__(self):
        with open('config.yaml', 'r') as config_file:
            cfg_dict = yaml.safe_load(config_file)

        # yes this is awkward but I don't care
        self.frames: int = int(cfg_dict['frames'])
        self.permutations: int = int(cfg_dict['permutations'])
        self.axis: str = str(cfg_dict['axis'])
        self.pos_init: float = float(cfg_dict['pos_init'])
        self.speed_init: float = float(cfg_dict['speed_init'])
        self.jump_timer: int = int(cfg_dict['jump_timer'])
        self.jump_speed: float = float(cfg_dict['jump_speed'])
        self.goal_position: float = float(cfg_dict['goal_position'])
        self.goal_direction: str = str(cfg_dict['goal_direction'])
        self.goal_speed: float = float(cfg_dict['goal_speed'])
        self.prioritize_speed: bool = bool(cfg_dict['prioritize_speed'])
        self.ducking: bool = bool(cfg_dict['ducking'])
        self.on_ground: bool = bool(cfg_dict['on_ground'])
        self.cold_core: bool = bool(cfg_dict['cold_core'])
        self.holdable_slow: bool = bool(cfg_dict['holdable_slow'])
        self.in_space: bool = bool(cfg_dict['in_space'])
        self.auto_jump: bool = bool(cfg_dict['auto_jump'])

        if self.axis not in ('x', 'y'):
            print("axis must be x or y, exiting")
            raise SystemExit
        if self.goal_direction not in ('-', '+'):
            print("axis must be - or +, exiting")
            raise SystemExit


def main():
    start_time = time.perf_counter()
    sys.stdout = Logger()
    cfg: Config = Config()
    print("building permutations...")
    input_permutations: tuple = build_input_permutations(cfg)
    valid_permutations: List[Tuple[float, float, tuple]] = []
    permutation: tuple
    print("\nsimulating inputs...")

    for permutation in tqdm.tqdm(input_permutations, ncols=100):
        results_pos: float
        results_speed: float

        if cfg.axis == 'x':
            results_pos, results_speed = sim_x(permutation, cfg)
        else:
            results_pos, results_speed = sim_y(permutation, cfg)

        if (cfg.goal_direction == '-' and results_pos < cfg.goal_position) or (cfg.goal_direction == '+' and results_pos > cfg.goal_position):
            append_permutation: bool = True
            valid_permutation: Tuple[float, float, tuple]

            for valid_permutation in valid_permutations:
                if results_pos == valid_permutation[0] and results_speed == valid_permutation[1]:
                    if len(permutation) < len(valid_permutation[2]):
                        valid_permutations.remove(valid_permutation)
                    else:
                        append_permutation = False
                        break

            if append_permutation:
                valid_permutations.append((results_pos, results_speed, permutation))

    if cfg.prioritize_speed:
        valid_permutations.sort(reverse=cfg.goal_direction == '+', key=lambda p: p[0])
        valid_permutations.sort(reverse=cfg.goal_direction == '-', key=lambda p: abs(p[1] - cfg.goal_speed))
    else:
        valid_permutations.sort(reverse=cfg.goal_direction == '-', key=lambda p: abs(p[1] - cfg.goal_speed))
        valid_permutations.sort(reverse=cfg.goal_direction == '+', key=lambda p: p[0])

    print("\ndone, outputting (useful inputs are at the bottom btw)\n")
    end_time = time.perf_counter()

    for valid_permutation in valid_permutations:
        print(valid_permutation)

    print(f"\nframes: {cfg.frames}")
    print(f"total permutations: {len(input_permutations)}")
    print(f"shown permutations: {len(valid_permutations)}")
    print(f"processing time: {round(end_time - start_time, 3)} s")


def sim_x(inputs: tuple, cfg: Config) -> Tuple[float, float]:
    x: float = cfg.pos_init
    speed_x: float = cfg.speed_init
    input_line: Tuple[int, str]

    for input_line in inputs:
        input_frames: List[str] = [input_line[1]] * input_line[0]
        input_key: str

        for input_key in input_frames:
            # celeste code (from Player.NormalUpdate) somewhat loosely translated from C# to python

            # get inputs first
            move_x: float = {'l': -1.0, '': 0.0, 'r': 1.0}[input_key]

            # calculate speed second
            if cfg.ducking and cfg.on_ground:
                speed_x = approach(speed_x, 0.0, 500.0 / 60.0)
            else:
                num1: float = 1.0 if cfg.on_ground else 0.65

                if cfg.on_ground and cfg.cold_core:
                    num1 *= 0.3

                # ignored low friction variant stuff

                if cfg.holdable_slow:
                    num2: float = 70.0
                else:
                    num2 = 90.0

                if cfg.in_space:
                    num2 *= 0.6

                if abs(speed_x) <= num2 or (0.0 if speed_x == 0.0 else float(math.copysign(1, speed_x))) != move_x:
                    speed_x = approach(speed_x, num2 * move_x, 1000.0 / 60.0 * num1)
                else:
                    speed_x = approach(speed_x, num2 * move_x, 400.0 / 60.0 * num1)

            # calculate position third
            x += speed_x / 60.0

    return float(round(x, 10)), float(round(speed_x, 10))


def sim_y(inputs: tuple, cfg: Config) -> Tuple[float, float]:
    y: float = cfg.pos_init
    speed_y: float = cfg.speed_init
    max_fall: float = 160.0
    jump_timer: int = cfg.jump_timer
    input_line: Tuple[int, str]

    for input_line in inputs:
        input_frames: List[str] = [input_line[1]] * input_line[0]
        input_key: str

        for input_key in input_frames:
            # celeste code (from Player.NormalUpdate) somewhat loosely translated from C# to python

            # get inputs first
            move_y: int = {'j': 0, '': 0, 'd': 1}[input_key]
            jump: bool = input_key == 'j'

            # calculate speed second
            target1: float = 160.0
            target2: float = 240.0

            if cfg.in_space:
                target1 *= 0.6
                target2 *= 0.6

            # ignored some weird holdable stuff

            if move_y == 1 and speed_y >= target1:
                max_fall = approach(max_fall, target2, 300.0 / 60.0)
            else:
                max_fall = approach(max_fall, target1, 300.0 / 60.0)

            # this line was kinda translated more using my experience from TASing than from actually translating the code so it may be wrong
            num: float = 0.5 if (abs(speed_y) <= 40.0 and (jump or cfg.auto_jump)) else 1.0

            if cfg.in_space:
                num *= 0.6

            speed_y = approach(speed_y, max_fall, (900.0 * num) / 60.0)

            if jump_timer > 0:
                if cfg.auto_jump or jump:
                    speed_y = min(speed_y, cfg.jump_speed)
                else:
                    jump_timer = 0

            jump_timer -= 1

            # calculate position third
            y += speed_y / 60.0

    return float(round(y, 10)), float(round(speed_y, 10))


def approach(val: float, target: float, max_move: float) -> float:
    if val <= target:
        return min(val + max_move, target)
    else:
        return max(val - max_move, target)


def build_input_permutations(cfg: Config) -> tuple:
    input_permutations: List[tuple] = []

    if cfg.axis == 'x':
        keys = ('l', '', 'r')
    else:
        keys = ('j', '', 'd')

    for _ in tqdm.tqdm(range(cfg.permutations), ncols=100):
        inputs: List[Tuple[int, str]] = []
        frame_counter = 0

        while frame_counter < cfg.frames:
            frames = round(random.randint(1, cfg.frames - frame_counter))
            frame_counter += frames
            inputs.append((frames, random.choice(keys)))

        input_permutations.append(tuple(inputs))

    input_permutations_tuple: tuple = tuple(input_permutations)
    del input_permutations
    return input_permutations_tuple


# log all prints to a file
class Logger(object):
    def __init__(self):
        if os.path.isfile('out.txt'):
            os.remove('out.txt')

        self.terminal = sys.stdout
        self.log = open('out.txt', 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        pass


if __name__ == '__main__':
    main()
