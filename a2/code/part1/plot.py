import numpy as np

import matplotlib.pyplot as plt

# Generate some data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create the plot
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('X-axis')
plt.ylabel('Y-axis')

# Save the plot as a .png file
plt.savefig('/Users/jaskaransinghbhalla/Work/courses/col334/a2/code/part1/plot.png')