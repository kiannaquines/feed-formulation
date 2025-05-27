from .config import *
import hmac
import hashlib
import struct
import time

def get_time_counter(interval=NEXT_OTP_INTERVAL):
    return int(time.time() // interval)

def truncate(hmac_digest):
    offset = hmac_digest[-1] & 0x0F
    binary = ((hmac_digest[offset] & 0x7f) << 24 |
              (hmac_digest[offset + 1] & 0xff) << 16 |
              (hmac_digest[offset + 2] & 0xff) << 8 |
              (hmac_digest[offset + 3] & 0xff))
    return binary

def generate_otp(secret_key: str, interval=NEXT_OTP_INTERVAL, digits=TOP_MAX_DIGIT):
    counter = get_time_counter(interval)
    key_bytes = secret_key.encode()
    counter_bytes = struct.pack(">Q", counter)
    hmac_digest = hmac.new(key_bytes, counter_bytes, hashlib.sha256).digest()
    otp = truncate(hmac_digest) % (10 ** digits)
    return str(otp).zfill(digits)

def verify_otp(secret_key: str, user_input_otp: str, interval=NEXT_OTP_INTERVAL, digits=TOP_MAX_DIGIT, tolerance=1):
    """
    Verifies the OTP by checking within ±tolerance time windows (default: 60s before/after).
    """
    current_counter = get_time_counter(interval)
    key_bytes = secret_key.encode()

    for offset in range(-tolerance, tolerance + 1):
        counter = current_counter + offset
        counter_bytes = struct.pack(">Q", counter)
        hmac_digest = hmac.new(key_bytes, counter_bytes, hashlib.sha256).digest()
        otp = truncate(hmac_digest) % (10 ** digits)
        expected_otp = str(otp).zfill(digits)

        if expected_otp == user_input_otp:
            return True

    return False