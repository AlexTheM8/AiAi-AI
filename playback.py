import pickle

import neat

from aiai_ai import conduct_genome

config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                     neat.DefaultSpeciesSet, neat.DefaultStagnation,
                     'config-feedforward')

p = neat.Population(config)

p.add_reporter(neat.StdOutReporter(True))
p.add_reporter(neat.StatisticsReporter())

with open('winner.pkl', 'rb') as input_file:
    genome = pickle.load(input_file)

conduct_genome(genome, config, 'REPLAY', p)
