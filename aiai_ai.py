import logging
from enum import Enum
from optparse import OptionParser
from os import listdir, mkdir, path
from pickle import dump
from time import perf_counter, sleep
from warnings import filterwarnings

import cv2
import neat
import numpy as np
import win32gui
from mss import mss as sct
from skimage.metrics import structural_similarity as compare_ssim
from torch import hub

from controller import Controller


class LogOptions(Enum):
    FULL = 'full'
    PARTIAL = 'partial'
    NONE = 'none'


def create_logger(option):
    log = logging.getLogger("Aiai_AI")
    log.handlers.clear()
    log.setLevel(logging.DEBUG)
    log.propagate = False

    if option != LogOptions.NONE.value:
        console_handle = logging.StreamHandler()
        console_handle.setLevel(logging.DEBUG)

        log_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S')
        console_handle.setFormatter(log_format)

        log.addHandler(console_handle)
    return log


def get_img():
    img = np.array(sct().grab(monitor))
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


# TODO Bottle neck
def detect_goal(img):
    g = -25
    ref = model(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), size=320)
    results = ref.xyxy[0]
    if len(results) > 0:
        x1, y1, x2, y2, prob, _ = results[0]
        if prob > 0.855:
            x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
            g = min((((x2 - x1) * (y2 - y1)) / (width * height)) * 125, 50)
            if g > 30:
                logger.info(f'prob: {prob}, g: {g}')
    return g


def interpret_and_act(img, x_input, y_input, st, g_max):
    done, info = False, ''

    controller.do_movement(x_input, y_input)

    # TODO Parallelize
    if img_similarity(img, time_over, to_shape):
        g_max -= 25  # [-25, 25]
        done, info = True, 'Time Over'
    elif img_similarity(img, fall_out, fo_shape):
        g_max -= 25  # [-50, 0] TODO Testing
        done, info = True, 'Fall Out'
    elif img_similarity(img, goal, g_shape):
        g_max = 30 + (1.25 * (60 - (perf_counter() - st)))  # [30, 105]
        done, info = True, 'Goal'

    if not done:
        g_max = max(g_max, detect_goal(img))

    return g_max, done, info


def conduct_genome(genome, cfg, genome_id, pop=None):
    global p

    p = p if pop is None else pop

    net = neat.nn.recurrent.RecurrentNetwork.create(genome, cfg)

    sleep(2.5)  # Allow time to load up

    current_max_fitness, g_max, step, zero_step, done = 0, 0, 0, 0, False

    controller.load_state()
    if options.logging == LogOptions.FULL.value:
        logger.info(f'running genome {genome_id} in generation {p.generation}')
    st = perf_counter()
    # step_list = np.array([])
    while not done:
        # step_time = perf_counter()
        # TODO Consistent intervals (investigate further) or pause during comp
        # get next image
        img = get_img()

        img_copy = cv2.resize(img, (inx, iny))
        img_copy = np.reshape(img_copy, (inx, iny, inc))

        img_array = np.ndarray.flatten(img_copy)

        # Get end result input to game
        x_input, y_input = net.activate(img_array)

        g_max, done, info = interpret_and_act(img, x_input, y_input, st, g_max)

        if info != '' and options.logging == LogOptions.FULL.value:
            logger.info(f'{info}')

        if g_max > current_max_fitness:
            current_max_fitness = g_max
            step, zero_step = 0, 0
        # TODO Review threshold
        elif options.zero_kill:
            if img_similarity(img, zero_mph, zm_shape, threshold=0.94):
                zero_step += 60
            step += 1
        else:
            step += 1
        if not done and (step > max_steps or zero_step > max_steps):
            done = True
            if step > max_steps or zero_step > max_steps:
                if options.logging == LogOptions.FULL.value:
                    logger.info('Timed out due to stagnation')
                g_max -= 25
        genome.fitness = g_max
        # step_list = np.append(step_list, perf_counter() - step_time)
    logger.info(f'generation: {p.generation}, genome: {genome_id}, fitness: {genome.fitness}')
    controller.do_movement(0, 0)  # Reset movement
    # logger.info(np.average(step_list))
    return genome.fitness


def update_stats(gen, sr, file='stats.csv'):
    with open(file, 'a') as f:
        f.write(','.join([str(gen), str(max_fitness[gen]), str(sr.get_fitness_mean()[-1]),
                          str(sr.get_fitness_stdev()[-1])]) + '\n')


def eval_genomes(genomes, cfg):
    if len(stat_reporter.get_fitness_mean()) > 0 and options.stats:
        update_stats(p.generation - 1, stat_reporter)
    max_fit = -50
    for genome_id, genome in genomes:
        fit = conduct_genome(genome, cfg, genome_id)
        max_fit = max(max_fit, fit)
    max_fitness[p.generation] = max_fit


def enumHandler(hwnd, lParam):
    global window
    name = win32gui.GetWindowText(hwnd)
    if 'Dolphin' in name and 'Super Monkey Ball' in name:
        window = hwnd


if __name__ == '__main__':
    parser = OptionParser()

    parser.set_defaults(stats=True, zero_kill=True)

    parser.add_option('-l', '--logging', dest='logging', choices=[o.value for o in LogOptions],
                      help='Logging options: [full, partial, none]. (Default=full)', default=LogOptions.FULL.value)
    parser.add_option('-s', '--stats', dest='stats',
                      help='Enable this flag to stop saving evolution stats. (Default=true)', action='store_false')
    parser.add_option('-z', '--zero_kill', dest='zero_kill',
                      help='Enable this flag to stop killing genome at 0mph. (Default=true)', action='store_false')
    parser.add_option('--window_scale', '-w', dest='window_scale', type=float, default=1.0,
                      help='Scale of window size. Ex: 1.0, 1.25, 1.5 (Default=1.0)')

    options, args = parser.parse_args()

    # Controller
    controller = Controller()

    # Image setup
    window, width, height = None, 0, 0
    win32gui.EnumWindows(enumHandler, None)
    if window is not None:
        border_x, border_y = 7, 31
        x_pad, y_pad, width, height = win32gui.GetWindowRect(window)
        width -= x_pad
        height -= y_pad
        x_pad = int(x_pad * options.window_scale) + round((border_x + 1) * options.window_scale)
        y_pad = int(y_pad * options.window_scale) + round(border_y * options.window_scale)
        width = int(width * options.window_scale) - round((border_x * 2) * options.window_scale)
        height = int(height * options.window_scale) - round((border_y + 6.25) * options.window_scale)
        monitor = {"top": y_pad, "left": x_pad, "width": width, "height": height}
    else:
        print('ERROR: Could not find SMB window')
        exit(-1)
    orig_width, orig_height, orig_x_pad, orig_y_pad, scale = 1300, 1000, 310, 30, 14
    rescale_w, rescale_h = width / orig_width, height / orig_height
    inx, iny, inc = width // scale, height // scale, 3
    rgb_low, rgb_up = np.array([0, 10, 0]), np.array([120, 255, 100])

    # Reference images
    time_over = cv2.imread('images/time_over.png')
    time_over = cv2.resize(time_over, (int(time_over.shape[1] * rescale_w), int(time_over.shape[0] * rescale_h)))
    to_x_pad, to_y_pad = 405 * rescale_w, 460 * rescale_h
    to_shape = (int(to_x_pad) - int(orig_x_pad * rescale_w), int(to_y_pad) - int(orig_y_pad * rescale_h))

    goal = cv2.imread('images/goal.png')
    goal = cv2.resize(goal, (int(goal.shape[1] * rescale_w), int(goal.shape[0] * rescale_h)))
    g_x_pad, g_y_pad = 700 * rescale_w, 635 * rescale_h
    g_shape = (int(g_x_pad) - int(orig_x_pad * rescale_w), int(g_y_pad) - int(orig_y_pad * rescale_h))

    fall_out = cv2.imread('images/fall_out.png')
    fall_out = cv2.resize(fall_out, (int(fall_out.shape[1] * rescale_w), int(fall_out.shape[0] * rescale_h)))
    fo_x_pad, fo_y_pad = 430 * rescale_w, 445 * rescale_h
    fo_shape = (int(fo_x_pad) - int(orig_x_pad * rescale_w), int(fo_y_pad) - int(orig_y_pad * rescale_h))

    zero_mph = cv2.imread('images/zeromph.png')
    zero_mph = cv2.resize(zero_mph, (int(zero_mph.shape[1] * rescale_w), int(zero_mph.shape[0] * rescale_h)))
    zm_x_pad, zm_y_pad = (410 * rescale_w) - (orig_x_pad * rescale_w), (880 * rescale_h) - (orig_y_pad * rescale_h)
    zm_shape = (int(zm_x_pad), int(zm_y_pad) + 3)

    # Goal detection
    filterwarnings("ignore", category=UserWarning)
    filterwarnings("ignore", category=RuntimeWarning)
    model = hub.load('yolov5', 'custom', 'yolov5/runs/train/exp/weights/best.pt', source='local')

    max_steps = 2000
    max_fitness = {}

    logger = create_logger(options.logging)

    # Network setup
    hist_path = 'history'
    checkpointer = neat.Checkpointer(generation_interval=1, filename_prefix=f'{hist_path}/neat-checkpoint-')
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         'config-feedforward')
    if not path.isdir(hist_path):
        mkdir(hist_path)
    if len(listdir(hist_path)) > 0:
        m = max([int(f[f.rfind('-') + 1:]) for f in listdir(hist_path)])
        p = checkpointer.restore_checkpoint(f'{hist_path}/neat-checkpoint-{m}')
        p.generation += 1
        logger.info(f'Restoring checkpoint {m}')
        p.config = config
    else:
        p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    stat_reporter = neat.StatisticsReporter()
    p.add_reporter(stat_reporter)
    p.add_reporter(checkpointer)

    # Final
    winner = p.run(eval_genomes)

    with open('winner.pkl', 'wb') as output:
        dump(winner, output, 1)
