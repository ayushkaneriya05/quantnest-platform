import numpy as np
import numba

@numba.njit(cache=True)
def _fast_crosses_above(arr1, arr2):
    res = np.zeros(len(arr1), dtype=np.bool_)
    for i in range(1, len(arr1)):
        res[i] = (arr1[i] > arr2[i]) and (arr1[i-1] <= arr2[i-1])
    return res

@numba.njit(cache=True)
def _fast_crosses_below(arr1, arr2):
    res = np.zeros(len(arr1), dtype=np.bool_)
    for i in range(1, len(arr1)):
        res[i] = (arr1[i] < arr2[i]) and (arr1[i-1] >= arr2[i-1])
    return res

@numba.njit(cache=True)
def fast_ffill_align_bool(source_times, source_vals, target_times):
    """
    O(1) amortized pointer referencing for MTF alignment of boolean arrays.
    """
    out = np.zeros(len(target_times), dtype=np.bool_)
    s_idx = 0
    s_len = len(source_times)
    
    if s_len == 0:
        return out
        
    current_val = source_vals[0]
    
    for t_idx in range(len(target_times)):
        t_time = target_times[t_idx]
        while s_idx + 1 < s_len and source_times[s_idx + 1] <= t_time:
            s_idx += 1
            current_val = source_vals[s_idx]
            
        if t_time >= source_times[0]:
            out[t_idx] = current_val
            
    return out

@numba.njit(cache=True)
def fast_ffill_align_float(source_times, source_vals, target_times):
    """
    O(1) amortized pointer referencing for MTF alignment of float arrays.
    """
    out = np.full(len(target_times), np.nan, dtype=np.float64)
    s_idx = 0
    s_len = len(source_times)
    
    if s_len == 0:
        return out
        
    current_val = source_vals[0]
    
    for t_idx in range(len(target_times)):
        t_time = target_times[t_idx]
        while s_idx + 1 < s_len and source_times[s_idx + 1] <= t_time:
            s_idx += 1
            current_val = source_vals[s_idx]
            
        if t_time >= source_times[0]:
            out[t_idx] = current_val
            
    return out



@numba.njit(cache=True)
def fast_sma(close_arr, period):
    out = np.full(len(close_arr), np.nan, dtype=np.float64)
    if len(close_arr) < period:
        return out
    
    # Initial SMA
    current_sum = np.sum(close_arr[:period])
    out[period-1] = current_sum / period
    
    for i in range(period, len(close_arr)):
        current_sum = current_sum - close_arr[i-period] + close_arr[i]
        out[i] = current_sum / period
        
    return out

@numba.njit(cache=True)
def fast_ema(close_arr, period):
    out = np.full(len(close_arr), np.nan, dtype=np.float64)
    if len(close_arr) < period:
        return out
        
    alpha = 2.0 / (period + 1)
    
    # Initial SMA
    ema = np.sum(close_arr[:period]) / period
    out[period-1] = ema
    
    for i in range(period, len(close_arr)):
        ema = (close_arr[i] - ema) * alpha + ema
        out[i] = ema
        
    return out