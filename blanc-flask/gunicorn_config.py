bind = "0.0.0.0:5000"
workers = 5  # (2 x $num_cores) + 1
threads = 2
timeout = 120

# https://medium.com/@nhudinhtuan/gunicorn-worker-types-practice-advice-for-better-performance-7a299bb8f929