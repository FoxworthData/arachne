from datetime import datetime, timedelta

timestamp_ms = 1747807598699
timestamp_ms = 1747858547212
timestamp_ms = 1747859877797
timestamp_ms = 1747860315936
timestamp_s = timestamp_ms / 1000  # Convert milliseconds to seconds

dt = datetime.utcfromtimestamp(timestamp_s)

print(f"{timestamp_ms} == {dt.strftime('%Y-%m-%d %H:%M:%S.%f')}")

mod_datetime = dt - timedelta(seconds=1)
print(f"{timestamp_ms} - 1 second == {mod_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')}")
print(f"{timestamp_ms} - 1 second == {int(mod_datetime.timestamp() * 1000)}")

# 1747860315936
# 1747878314936

# Current UTC datetime
now = datetime.utcnow()

# Current timestamp (in seconds)
current_timestamp = int(now.timestamp())

# Timestamp 7 days in the future
future = now + timedelta(hours=12)
future_timestamp = int(future.timestamp())

print("Now:", current_timestamp)
print("12 hours from now:", future_timestamp)