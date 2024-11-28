import time
import pandas as pd


class StatisticsLogger:
    def __init__(self):
        self.stats = {
            "operation": [],
            "filename": [],
            "start_time": [],
            "end_time": [],
            "elapsed_time": [],
            "file_size": [],
            "data_rate": [],
            "response_time": [],
        }

    def start_timer(self):
        """Start timer for an operation"""
        return time.time()

    def end_timer(self, start_time, operation, filename="", file_size=0, elapsed_time=0, response_time=0):
        """Record statistics for an operation"""
        end_time = time.time()
        data_rate = file_size / elapsed_time if elapsed_time > 0 else 0

        self.stats["operation"].append(operation)
        self.stats["filename"].append(filename)
        self.stats["start_time"].append(start_time)
        self.stats["end_time"].append(end_time)
        self.stats["elapsed_time"].append(elapsed_time)
        self.stats["response_time"].append(response_time)
        self.stats["file_size"].append(file_size)
        self.stats["data_rate"].append(data_rate)

    def save_to_file(self, file_path):
        """Save statistics to CSV file"""
        df = pd.DataFrame(self.stats)
        df.to_csv(file_path, index=False)

    def get_dataframe(self):
        """Return statistics as Pandas dataframe"""
        return pd.DataFrame(self.stats)