from generator import generate_system
from formatter import format_system
from output import print_system, save_system

key = "BenjaminHayes"

system    = generate_system(key)
formatted = format_system(system)

print_system(system)
save_system(system, formatted)
