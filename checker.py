import urllib.request
import http.cookiejar
import threading
import queue
import itertools
import time
from colorama import Fore, Back, Style

# Задайте значения по умолчанию для параметров
in_directory = ''
out_filename = ''
test_url = ''
thread_number = 100
timeout_value = 10

ok_msg = Fore.GREEN + "OK!  " + Fore.RESET
fail_msg = Fore.RED + "FAIL " + Fore.RESET

good_proxy_num = itertools.count()
start_time = time.time()
end_time = time.time()

mylock = threading.Lock()

def sprint(*a, **b):
    with mylock:
        print(*a, **b)

class PrintThread(threading.Thread):
    def __init__(self, queue, filename):
        threading.Thread.__init__(self)
        self.queue = queue
        self.output = open(filename, 'a')
        self.shutdown = False

    def write(self, line):
        print(line, file=self.output)

    def run(self):
        while not self.shutdown:
            lines = self.queue.get()
            self.write(lines)
            self.queue.task_done()

    def terminate(self):
        self.output.close()
        self.shutdown = True

class ProcessThread(threading.Thread):
    def __init__(self, id, task_queue, out_queue):
        threading.Thread.__init__(self)
        self.task_queue = task_queue
        self.out_queue = out_queue
        self.id = id

    def run(self):
        while True:
            task = self.task_queue.get()
            result = self.process(task)

            if result is not None:
                self.out_queue.put(result)
                next(good_proxy_num)

            self.task_queue.task_done()

    def process(self, task):
        proxy = task
        log_msg = str(f"Thread #{self.id:3d}.  Trying HTTP proxy {proxy:21s}\t\t")

        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPRedirectHandler(),
            urllib.request.ProxyHandler({'http': proxy})
        )

        try:
            t1 = time.time()
            response = opener.open(test_url, timeout=timeout_value).read()
            t2 = time.time()
        except Exception as e:
            log_msg += f"{fail_msg} ({str(e)})"
            sprint(log_msg)
            return None

        log_msg += f"{ok_msg} Response time: {int((t2 - t1) * 1000)} ms, length={len(response)}"
        sprint(log_msg)
        return proxy

    def terminate(self):
        None

input_queue = queue.Queue()
result_queue = queue.Queue()

workers = []

# Создание и запуск потоков обработки
for i in range(thread_number):
    t = ProcessThread(i, input_queue, result_queue)
    t.setDaemon(True)
    t.start()
    workers.append(t)

f_printer = PrintThread(result_queue, out_filename)
f_printer.setDaemon(True)
f_printer.start()

start_time = time.time()

proxy_list = []

# Загрузка прокси из файлов в указанной директории
import os

for root, dirs, files in os.walk(in_directory):
    for file in files:
        if file.endswith(".txt"):
            file_line_list = [line.rstrip('\n') for line in open(os.path.join(root, file), 'r')]
            proxy_list.extend(file_line_list)

# Помещение прокси в очередь для обработки
for proxy in proxy_list:
    input_queue.put(proxy)

total_proxy_num = len(proxy_list)
print(f"Got {total_proxy_num} proxies to check")

if total_proxy_num == 0:
    exit()

input_queue.join()
result_queue.join()

f_printer.terminate()

# Завершение работы потоков обработки
for worker in workers:
    worker.terminate()

good_proxy_num = float(next(good_proxy_num))
print(f"In: {total_proxy_num}. Good: {good_proxy_num}, that's {100.0 * good_proxy_num / total_proxy_num:.2f}%")

end_time = time.time()
print(f"Time elapsed: {end_time - start_time:.1f} seconds.")
