import os
import pickle
import time
import warnings
from functools import partial

import cv2
import neat
import numpy as np
import pyautogui
from PIL import ImageGrab
from skimage.metrics import structural_similarity as compare_ssim
from torch import hub

from controller import Controller


def get_ts():
    return time.strftime("%H:%M:%S", time.localtime())


def get_img():
    img = pyautogui.screenshot(region=(x_pad, y_pad, width, height))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def img_similarity(img, compare, shape, threshold=0.75):
    crop = img[shape[1]:shape[1] + compare.shape[0], shape[0]:shape[0] + compare.shape[1]]

    # Chroma key
    mask = cv2.inRange(compare, rgb_low, rgb_up)
    com_copy, crop_copy = np.copy(compare), np.copy(crop)

    com_copy = compare - cv2.bitwise_and(com_copy, com_copy, mask=mask)
    crop_copy = crop - cv2.bitwise_and(crop_copy, crop_copy, mask=mask)

    # Convert to grayscale
    crop_copy = cv2.cvtColor(crop_copy, cv2.COLOR_BGR2GRAY)
    com_copy = cv2.cvtColor(com_copy, cv2.COLOR_BGR2GRAY)

    return compare_ssim(com_copy, crop_copy) > threshold


def interpret_and_act(img, x_input, y_input, st, g_max):
    done, info = False, ''

    controller.do_movement(x_input, y_input)

    ref = model(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), size=640)
    results = ref.xyxy[0]
    if len(results) > 0:
        x1, y1, x2, y2, prob, _ = results[0]
        if prob > 0.55:
            x1, y1, x2, y2, prob = float(x1), float(y1), float(x2), float(y2), float(prob)
            g = min((((x2 - x1) * (y2 - y1)) / (width * height)) * 150, 50)
            if g > g_max:
                g_max = g

    if img_similarity(img, time_over, to_shape):
        g_max -= 25  # [-25, 25]
        done, info = True, 'Time Over'
    elif img_similarity(img, fall_out, fo_shape):
        g_max -= 50  # [-50, 0]
        done, info = True, 'Fall Out'
    elif img_similarity(img, goal, g_shape):
        g_max = 30 + (1.25 * (60 - (time.time() - st)))  # [30, 105]
        done, info = True, 'Goal'

    return g_max, done, info


def conduct_genome(genome, cfg, genome_id, pop=None):
    global p
    if pop is not None:
        p = pop
    net = neat.nn.recurrent.RecurrentNetwork.create(genome, cfg)

    time.sleep(1.85)

    current_max_fitness, g_max, step, zero_step, done = 0, 0, 0, 0, False

    controller.load_state()
    print(f'{get_ts()}: INFO: running genome {genome_id} in generation {p.generation}')
    st = time.time()
    while not done:
        # TODO Consistent intervals (investigate further)
        # get next image
        img = get_img()

        img_copy = cv2.resize(img, (inx, iny))
        img_copy = np.reshape(img_copy, (inx, iny, inc))

        img_array = np.ndarray.flatten(img_copy)

        # Get end result input to game
        x_input, y_input = net.activate(img_array)

        g_max, done, info = interpret_and_act(img, x_input, y_input, st, g_max)
        if info != '':
            print(f'{get_ts()}: {info}')

        if g_max > current_max_fitness:
            current_max_fitness = g_max
            step, zero_step = 0, 0
        elif img_similarity(img, zero_mph, zm_shape, threshold=0.95):
            zero_step += 60
        else:
            step += 1
            zero_step = 0
        if done or step > max_steps or zero_step > max_steps:
            done = True
            if step > max_steps or zero_step > max_steps:
                print(f'{get_ts()}: INFO: Timed out due to stagnation')
                g_max -= 25
            print(f'{get_ts()}: INFO: generation: {p.generation}, genome: {genome_id}, fitness: {g_max}')
        genome.fitness = g_max
    controller.do_movement(0, 0)  # Reset movement
    return genome.fitness


def update_stats(gen, sr, file='stats.csv'):
    with open(file, 'a') as f:
        f.write(','.join([str(gen), str(max_fitness[gen]), str(sr.get_fitness_mean()[-1]),
                          str(sr.get_fitness_stdev()[-1])]) + '\n')


def eval_genomes(genomes, cfg):
    if len(stat_reporter.get_fitness_mean()) > 0:
        update_stats(p.generation-1, stat_reporter)
    max_fit = -50
    for genome_id, genome in genomes:
        fit = conduct_genome(genome, cfg, genome_id)
        max_fit = max(max_fit, fit)
    max_fitness[p.generation] = max_fit


# Controller
controller = Controller()

# Image setup
ImageGrab.grab = partial(ImageGrab.grab, all_screens=True)
width, height, x_pad, y_pad, scale = 1300, 1000, 310, 30, 25
inx, iny, inc = width // scale, height // scale, 3
rgb_low, rgb_up = np.array([0, 10, 0]), np.array([120, 255, 100])

# Reference images
time_over = cv2.imread('images/time_over.png')
to_x_pad, to_y_pad = 405, 460
to_shape = (to_x_pad - x_pad, to_y_pad - y_pad)

goal = cv2.imread('images/goal.png')
g_x_pad, g_y_pad = 700, 635
g_shape = (g_x_pad - x_pad, g_y_pad - y_pad)

fall_out = cv2.imread('images/fall_out.png')
fo_x_pad, fo_y_pad = 430, 445
fo_shape = (fo_x_pad - x_pad, fo_y_pad - y_pad)

zero_mph = cv2.imread('images/zeromph.png')
zm_x_pad, zm_y_pad = 410, 880
zm_shape = (zm_x_pad - x_pad, zm_y_pad - y_pad)

# Goal detection
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
model = hub.load('yolov5', 'custom', 'yolov5/runs/train/exp/weights/best.pt', source='local')

max_steps = 500

if __name__ == '__main__':
    # TODO Flag for logging (options={full, partial, none} where partial includes stdout & non-timeouts)
    # TODO Flag for stat-saving

    # Network setup
    checkpointer = neat.Checkpointer(generation_interval=1, filename_prefix='history/neat-checkpoint-')
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         'config-feedforward')
    if len(os.listdir('history')) > 0:
        m = max([int(f[f.rfind('-') + 1:]) for f in os.listdir('history')])
        p = checkpointer.restore_checkpoint(f'history/neat-checkpoint-{m}')
        p.generation += 1
        print(f'{get_ts()}: Restoring checkpoint {m}')
        p.config = config
    else:
        p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    stat_reporter = neat.StatisticsReporter()
    p.add_reporter(stat_reporter)
    p.add_reporter(checkpointer)

    max_fitness = {}

    # Final
    winner = p.run(eval_genomes)

    with open('winner.pkl', 'wb') as output:
        pickle.dump(winner, output, 1)
