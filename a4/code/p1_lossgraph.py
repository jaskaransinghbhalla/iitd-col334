import pandas as pd
import matplotlib.pyplot as plt

# Load the data from the CSV file
data = pd.read_csv('reliability_loss.csv')

# Group by 'loss' and calculate the mean of 'ttc' for both fast_recovery=True and fast_recovery=False
mean_ttc_fast_recovery = data[data['fast_recovery'] == True].groupby('loss')['ttc'].mean()
mean_ttc_without_fast_recovery = data[data['fast_recovery'] == False].groupby('loss')['ttc'].mean()

# Write the values to csv file



# Plot the data
plt.figure(figsize=(10, 6))
plt.plot(mean_ttc_fast_recovery.index, mean_ttc_fast_recovery.values, label='With Fast Recovery', marker='o', color='b')
plt.plot(mean_ttc_without_fast_recovery.index, mean_ttc_without_fast_recovery.values, label='Without Fast Recovery', marker='x', color='r')

# Label the plot
plt.title('Average File Transmission Time vs Loss')
plt.xlabel('Loss (%)')
plt.ylabel('Average Transmission Time (s)')
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save the plot to a file
plt.savefig('transmission_time_vs_loss.png', dpi=300)  # Save with high quality

# Show the plot
plt.show()