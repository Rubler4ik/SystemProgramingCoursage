import multiprocessing
import time
import os
import psutil
import numpy as np
import pyopencl as cl
import logging
import csv
import random
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(filename='stress_test.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class StressTest:
    def __init__(self):
        self.errors = []

    def cpu_stress(self, duration=10, matrix_size=2000):
        """Нагружает CPU с использованием матричных вычислений."""
        def heavy_task():
            start_time = time.time()
            while time.time() - start_time < duration:
                a = np.random.rand(matrix_size, matrix_size)
                b = np.random.rand(matrix_size, matrix_size)
                np.dot(a, b)

        processes = []
        try:
            logging.info(f"Starting CPU stress test for {duration} seconds, matrix size {matrix_size}x{matrix_size}")
            for _ in range(multiprocessing.cpu_count()):
                p = multiprocessing.Process(target=heavy_task)
                p.start()
                processes.append(p)
            time.sleep(duration)
        except Exception as e:
            self.errors.append(f"CPU test error: {str(e)}")
            logging.error(f"CPU test error: {str(e)}")
        finally:
            for p in processes:
                p.terminate()
                p.join()
        logging.info(f"CPU stress test completed ({duration} seconds).")

    def ram_stress(self, duration=10, size_mb=128):
        """Нагружает RAM, измеряет последовательный и случайный доступ."""
        ram = psutil.virtual_memory()
        free_mb = ram.free / (1024 ** 2)
        size_mb = min(size_mb, int(free_mb * 0.5))  # Используем не более 50% свободной памяти
        if size_mb < 10:
            error = f"Not enough free RAM ({free_mb:.2f} MB available, minimum 10 MB needed)"
            self.errors.append(error)
            logging.error(error)
            return 0, 0, 0, 0

        size = int(size_mb * 1024 * 1024 / 8)
        seq_speeds = []
        rand_speeds = []
        seq_latencies = []
        rand_latencies = []
        start_time = time.time()
        arrays = []
        try:
            logging.info(f"Starting RAM stress test for {duration} seconds, size {size_mb} MB")
            while time.time() - start_time < duration:
                # Последовательный доступ
                t_start = time.time()
                arr = np.zeros(size, dtype=np.float64)
                arrays.append(arr)
                for i in range(size):
                    arr[i] = i
                seq_write_time = time.time() - t_start
                seq_speed = size_mb / seq_write_time
                seq_speeds.append(seq_speed)

                t_start = time.time()
                _ = arr[size - 1]
                seq_latency = (time.time() - t_start) * 1000
                seq_latencies.append(seq_latency)

                # Случайный доступ
                t_start = time.time()
                indices = np.random.randint(0, size, size=1000)
                for i in indices:
                    arr[i] = i
                rand_write_time = time.time() - t_start
                rand_speed = (1000 * 8 / 1024 / 1024) / rand_write_time
                rand_speeds.append(rand_speed)

                t_start = time.time()
                _ = arr[np.random.randint(0, size)]
                rand_latency = (time.time() - t_start) * 1000
                rand_latencies.append(rand_latency)

                time.sleep(0.1)
        except Exception as e:
            self.errors.append(f"RAM test error: {str(e)}")
            logging.error(f"RAM test error: {str(e)}")
        finally:
            arrays.clear()
        avg_seq_speed = sum(seq_speeds) / len(seq_speeds) if seq_speeds else 0
        avg_rand_speed = sum(rand_speeds) / len(rand_speeds) if rand_speeds else 0
        avg_seq_latency = sum(seq_latencies) / len(seq_latencies) if seq_latencies else 0
        avg_rand_latency = sum(rand_latencies) / len(rand_latencies) if rand_latencies else 0
        logging.info(
            f"RAM stress test completed ({duration} seconds, {size_mb} MB, "
            f"Seq Speed: {avg_seq_speed:.2f} MB/s, Seq Latency: {avg_seq_latency:.2f} ms, "
            f"Rand Speed: {avg_rand_speed:.2f} MB/s, Rand Latency: {avg_rand_latency:.2f} ms)"
        )

        with open("ram_test_results.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([time.time(), size_mb, avg_seq_speed, avg_seq_latency, avg_rand_speed, avg_rand_latency])

        return avg_seq_speed, avg_seq_latency, avg_rand_speed, avg_rand_latency

    def disk_stress(self, duration=10, file_size_mb=100):
        """Тест диска, аналогичный CrystalDiskMark."""
        temp_file = "temp_test_file.bin"
        file_size = file_size_mb * 1024 * 1024
        tests = [
            {"name": "Seq Q32T1", "block_size": 1 * 1024 * 1024, "queue_depth": 32, "threads": 1},
            {"name": "4K Q32T1", "block_size": 4 * 1024, "queue_depth": 32, "threads": 1},
            {"name": "Seq", "block_size": 1 * 1024 * 1024, "queue_depth": 1, "threads": 1},
            {"name": "4K Q1T1", "block_size": 4 * 1024, "queue_depth": 1, "threads": 1}
        ]
        results = {
            "seq_q32t1_read": [], "seq_q32t1_write": [],
            "4k_q32t1_read": [], "4k_q32t1_write": [],
            "seq_read": [], "seq_write": [],
            "4k_q1t1_read": [], "4k_q1t1_write": []
        }

        disk = psutil.disk_usage('/')
        free_space = disk.free / (1024 ** 2)
        if free_space < file_size_mb * 2:
            error = f"Not enough free space ({free_space:.2f} MB available, {file_size_mb * 2} MB needed)"
            self.errors.append(error)
            logging.error(error)
            return results

        def run_test(test, operation):
            name = test["name"].lower().replace(" ", "_")
            block_size = test["block_size"]
            queue_depth = test["queue_depth"]
            start_time = time.time()
            total_bytes = 0
            for _ in range(5):  # 5 проходов
                if operation == "write":
                    with open(temp_file, "wb") as f:
                        for _ in range(queue_depth):
                            f.write(os.urandom(block_size))
                            total_bytes += block_size
                else:
                    with open(temp_file, "rb") as f:
                        for _ in range(queue_depth):
                            if random.random() < 0.5:  # Случайное чтение для 4K
                                f.seek(random.randint(0, file_size - block_size))
                            f.read(block_size)
                            total_bytes += block_size
            elapsed = time.time() - start_time
            speed = (total_bytes / (1024 ** 2)) / elapsed
            results[f"{name}_{operation}"].append(speed)

        try:
            logging.info(f"Starting disk stress test for {duration} seconds, file size {file_size_mb} MB")
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=4) as executor:
                while time.time() - start_time < duration:
                    # Подготовка файла
                    with open(temp_file, "wb") as f:
                        f.write(os.urandom(file_size))
                    for test in tests:
                        executor.submit(run_test, test, "write")
                        executor.submit(run_test, test, "read")
                    time.sleep(1)
        except Exception as e:
            self.errors.append(f"Disk test error: {str(e)}")
            logging.error(f"Disk test error: {str(e)}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        avg_results = {k: sum(v) / len(v) if v else 0 for k, v in results.items()}
        logging.info(f"Disk stress test completed: {avg_results}")
        with open("disk_test_results.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([time.time()] + [avg_results[k] for k in results.keys()])
        return avg_results

    def gpu_stress(self, duration=10):
        """Нагружает GPU с помощью PyOpenCL."""
        try:
            logging.info(f"Starting GPU stress test for {duration} seconds")
            platform = cl.get_platforms()[0]
            device = platform.get_devices()[0]
            ctx = cl.Context([device])
            queue = cl.CommandQueue(ctx)

            size = 2048
            a = np.random.rand(size, size).astype(np.float32)
            b = np.random.rand(size, size).astype(np.float32)
            c = np.zeros((size, size), dtype=np.float32)

            mf = cl.mem_flags
            a_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
            b_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b)
            c_buf = cl.Buffer(ctx, mf.WRITE_ONLY, c.nbytes)

            prg = cl.Program(ctx, """
                __kernel void matmul(__global float *a, __global float *b, __global float *c, int size) {
                    int i = get_global_id(0);
                    int j = get_global_id(1);
                    float sum = 0;
                    for (int k = 0; k < size; k++) {
                        sum += a[i * size + k] * b[k * size + j];
                    }
                    c[i * size + j] = sum;
                }
            """).build()

            start_time = time.time()
            while time.time() - start_time < duration:
                prg.matmul(queue, (size, size), None, a_buf, b_buf, c_buf, np.int32(size))
                queue.finish()
        except Exception as e:
            self.errors.append(f"GPU test error: {str(e)}")
            logging.error(f"GPU test error: {str(e)}")
        logging.info(f"GPU stress test completed ({duration} seconds).")

    def get_errors(self):
        """Возвращает список ошибок."""
        return self.errors