import time
import random

def human_like_delay(min_sec=2, max_sec=5):
    time.sleep(random.uniform(min_sec, max_sec))