import threading
import concurrent.futures
import time

def A():
    for x in range(10):
        time.sleep(0.1)

start1 = time.time()
A()
A()
end1 = time.time()
print ('non threaded time is: ',end1-start1)

if __name__ == '__main__':
    start2 = time.time()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    futures = [executor.submit(A), executor.submit(A)]
    concurrent.futures.wait(futures)
    end2 = time.time()
    print ('threaded time is: ', end2-start2)
